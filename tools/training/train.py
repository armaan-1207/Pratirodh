"""Opt-in free-GPU QLoRA pilot; never invoked by the product launcher."""
import argparse
import hashlib
import json
from pathlib import Path

from prepare import BASE, REVISION, messages, validate


def load_data(directory):
    payload = (directory / 'examples.json').read_bytes()
    if len(payload) > 16_000_000:
        raise ValueError('Dataset exceeds 16 MB limit')
    receipt = json.loads((directory / 'dataset.json').read_text())
    if hashlib.sha256(payload).hexdigest() != receipt['dataset_sha256']:
        raise ValueError('Dataset hash mismatch')
    if (receipt['base_model'], receipt['base_revision']) != (BASE, REVISION):
        raise ValueError('Unexpected base model')
    rows = json.loads(payload)
    validate(rows)
    return rows, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    rows, receipt = load_data(args.data)
    if args.check:
        print(json.dumps(receipt, indent=2))
        return
    import torch
    if not torch.cuda.is_available() or torch.cuda.get_device_properties(0).total_memory < 14 * 1024 ** 3:
        raise RuntimeError('A free CUDA GPU with at least 14 GiB VRAM is required. No CPU or paid fallback.')
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                              DataCollatorForSeq2Seq, Trainer, TrainingArguments, set_seed)
    from transformers.trainer_utils import get_last_checkpoint
    config = {**receipt, 'seed': 1207, 'max_length': 1536, 'steps': 16,
              'rank': 8, 'learning_rate': 0.0001, 'status': 'pilot-not-promoted'}
    binding = args.output / 'training-inputs.json'
    if args.output.exists():
        if not args.resume or not binding.is_file() or json.loads(binding.read_text()) != config:
            raise ValueError('Existing output refused; resume requires identical training inputs')
    else:
        args.output.mkdir(parents=True)
        binding.write_text(json.dumps(config, indent=2), encoding='utf-8')
    set_seed(config['seed'])
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION, trust_remote_code=False)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'right'
    model = AutoModelForCausalLM.from_pretrained(BASE, revision=REVISION, trust_remote_code=False,
        use_safetensors=True, device_map={'': 0}, torch_dtype=torch.float16,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16))
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=.05,
        bias='none', task_type='CAUSAL_LM', target_modules=['q_proj','k_proj','v_proj','o_proj']))

    def encode(row):
        conversation = messages(row)
        prefix = tokenizer.apply_chat_template(conversation[:2], tokenize=True, add_generation_prompt=True)
        tokens = tokenizer.apply_chat_template(conversation, tokenize=True, add_generation_prompt=False)
        if len(tokens) > config['max_length'] or tokens[:len(prefix)] != prefix:
            raise ValueError('Example exceeds context or chat-template prefix changed; refusing truncation')
        return {'input_ids': tokens, 'attention_mask': [1]*len(tokens),
                'labels': [-100]*len(prefix)+tokens[len(prefix):]}
    datasets = {split: Dataset.from_list([encode(row) for row in rows if row['split'] == split])
                for split in ['train','validation']}
    training = TrainingArguments(output_dir=str(args.output), max_steps=16, per_device_train_batch_size=1,
        per_device_eval_batch_size=1, gradient_accumulation_steps=4, learning_rate=.0001,
        fp16=True, gradient_checkpointing=True, optim='paged_adamw_8bit', logging_steps=1,
        save_steps=4, save_total_limit=2, eval_strategy='steps', eval_steps=4,
        report_to='none', seed=1207, data_seed=1207, save_safetensors=True)
    trainer = Trainer(model=model,args=training,train_dataset=datasets['train'],eval_dataset=datasets['validation'],
        data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100))
    checkpoint = get_last_checkpoint(str(args.output)) if args.resume else None
    if args.resume and checkpoint is None:
        raise ValueError('No checkpoint exists to resume')
    result = trainer.train(resume_from_checkpoint=checkpoint)
    model.save_pretrained(args.output / 'adapter', safe_serialization=True)
    tokenizer.save_pretrained(args.output / 'adapter')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.output / 'adapter').iterdir() if p.is_file()}
    (args.output / 'training-result.json').write_text(json.dumps({**config, 'completed_steps':trainer.state.global_step,
        'metrics':result.metrics,'adapter_files':hashes,'promotion':'NOT_EVALUATED'},indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
