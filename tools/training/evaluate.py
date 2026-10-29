"""Generate paired pilot predictions; never execute generated source or claim promotion."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from prepare import BASE, REVISION, messages
from train import load_data


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--training', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args()
    if a.output.exists():
        raise ValueError('Existing predictions refused')
    rows, receipt=load_data(a.data)
    result=json.loads((a.training/'training-result.json').read_text())
    if result['dataset_sha256']!=receipt['dataset_sha256'] or result['completed_steps']!=16:
        raise ValueError('Training receipt does not match completed pilot')
    adapter=a.training/'adapter'
    if set(x.name for x in adapter.iterdir() if x.is_file())!=set(result['adapter_files']):
        raise ValueError('Adapter inventory changed')
    for name, expected in result['adapter_files'].items():
        if Path(name).name!=name or hashlib.sha256((adapter/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Adapter hash mismatch')
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    if not torch.cuda.is_available():
        raise RuntimeError('Free CUDA GPU required')
    tok=AutoTokenizer.from_pretrained(BASE, revision=REVISION, trust_remote_code=False)
    base=AutoModelForCausalLM.from_pretrained(BASE, revision=REVISION, trust_remote_code=False,
        use_safetensors=True, device_map={'':0}, torch_dtype=torch.float16,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
        bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16))
    model=PeftModel.from_pretrained(base,str(adapter),is_trainable=False)
    model.eval()
    predictions=[]
    for row in rows:
        if row['split']!='test': continue
        inputs=tok.apply_chat_template(messages(row)[:2],add_generation_prompt=True,
            tokenize=True,return_tensors='pt').to('cuda')
        if inputs.shape[1]>1536: raise ValueError('Prompt exceeds budget')
        for variant in ['base','candidate']:
            from contextlib import nullcontext
            start=time.monotonic()
            with torch.inference_mode(), (model.disable_adapter() if variant=='base' else nullcontext()):
                output=model.generate(inputs,attention_mask=torch.ones_like(inputs),
                    max_new_tokens=768,do_sample=False,pad_token_id=tok.eos_token_id,max_time=120)
            raw=tok.decode(output[0,inputs.shape[1]:],skip_special_tokens=True)
            predictions.append({'id':row['id'],'variant':variant,'cwe':row['cwe'],
                'output':raw,'elapsed_seconds':round(time.monotonic()-start,3),
                'generated_tokens':int(output.shape[1]-inputs.shape[1]),'model_calls':1})
            print(row['id'],variant,'generated',flush=True)
    a.output.write_text(json.dumps({'base_model':BASE,'base_revision':REVISION,
        'dataset_sha256':receipt['dataset_sha256'],'adapter_files':result['adapter_files'],
        'budget':{'max_new_tokens':768,'max_time_seconds':120,'calls_per_case_variant':1},
        'predictions':predictions,'verification':'NOT_EXECUTED','promotion':'NOT_EVALUATED'},indent=2))

if __name__=='__main__': main()
