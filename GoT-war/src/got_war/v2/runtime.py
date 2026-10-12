"""Version-separated execution; version 1 records and deadlines are read-only."""
import json
from pathlib import Path
from ..budget import Budget
from ..generation import Generator
from ..generation import SYSTEM


def budget(root):
    return Budget(root, 'budget_v2.json')


class V2Generator(Generator):
    def __init__(self, root):
        b = budget(root)
        # This is a pilot-only guard, not the final campaign token allowance.
        if b.config['output_token_ceiling'] is None:
            b.config['output_token_ceiling'] = 80000
        super().__init__(root, budget=b, results_dir='results/v2', prompt_dir='.private/prompts_v2')

    def call(self, role, prompt, max_tokens=2048, seed=2701, temperature=.2, schema=None, thinking=False):
        if not hasattr(self,'tokenizer'):
            from transformers import AutoTokenizer
            self.tokenizer=AutoTokenizer.from_pretrained(self.config['primary'],revision=self.config['revision'],
                local_files_only=True,cache_dir=str(self.root/'.cache/huggingface/hub'))
        system=SYSTEM.replace('/no_think','').strip() if thinking else SYSTEM
        count=len(self.tokenizer.apply_chat_template([{'role':'system','content':system},{'role':'user','content':prompt}],
            tokenize=True,add_generation_prompt=True,enable_thinking=thinking))
        allowance=self.config['max_model_len']-count-32
        if allowance<512:raise RuntimeError('Version 2 prompt exceeds the frozen context budget; split the artifact')
        return super().call(role,prompt,min(max_tokens,allowance),seed,temperature,schema,thinking)


def paths(root):
    root = Path(root)
    b = budget(root)
    result = root / 'results/v2'
    result.mkdir(parents=True, exist_ok=True)
    return root, b.run, result
