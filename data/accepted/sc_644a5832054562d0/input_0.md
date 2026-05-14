# PR #36630 diff (first 3000 characters) showing changes across multiple model files


# Seed Material: huggingface/transformers#36630: Add attention visualization tool 
Source: github_issue_pr
Identifier: pr:huggingface/transformers#36630

Repository: huggingface/transformers
PR Number: #36630
PR Title: Add attention visualization tool 
Merged At: 2025-03-19T12:58:46Z
Changed Files: 55
Additions: +294, Deletions: -59

## PR Description
# What does this PR do?

TODOS
- [ ] Add some tests
- [ ] make it work on all models

cc @yonigozlan and @zucchini-nlp @molbap 

This will be available as: 
```python

from transformers.utils.attention_visualizer import AttentionMaskVisualizer
visualizer = AttentionMaskVisualizer("meta-llama/Llama-3.2-3B-Instruct")
visualizer("A normal attention mask")

visualizer = AttentionMaskVisualizer("mistralai/Mistral-Small-24B-Instruct-2501")
visualizer("A normal attention mask with a long text to see how it is displayed, and if it is displayed correctly")

visualizer = AttentionMaskVisualizer("google/paligemma2-3b-mix-224")
visualizer("<img> You are an assistant.", suffix = "What is on the image?")

visualizer = AttentionMaskVisualizer("google/gemma-2b")
visualizer("You are an assistant. Make sure you print me") # we should have slidiing on non sliding side by side

visualizer = AttentionMaskVisualizer("google/gemma-3-27b-it")
visualizer("<img>You are an assistant. Make sure you print me") # we should have slidiing on non sliding side by side
```
![image](https://github.com/user-attachments/assets/d10f63f2-ad5e-4550-a30f-7181be554a67)

## Diff (first 3000 chars)
diff --git a/src/transformers/models/aria/modeling_aria.py b/src/transformers/models/aria/modeling_aria.py
index 252ddb694f31..e44cd709dfcf 100644
--- a/src/transformers/models/aria/modeling_aria.py
+++ b/src/transformers/models/aria/modeling_aria.py
@@ -1015,7 +1015,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/bloom/modeling_bloom.py b/src/transformers/models/bloom/modeling_bloom.py
index 504220c788b5..932787993344 100644
--- a/src/transformers/models/bloom/modeling_bloom.py
+++ b/src/transformers/models/bloom/modeling_bloom.py
@@ -747,7 +747,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/chameleon/modeling_chameleon.py b/src/transformers/models/chameleon/modeling_chameleon.py
index 3c3bcb4d0117..1f714bb05a82 100644
--- a/src/transformers/models/chameleon/modeling_chameleon.py
+++ b/src/transformers/models/chameleon/modeling_chameleon.py
@@ -1390,7 +1390,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/codegen/modeling_codegen.py b/src/transformers/models/codegen/modeling_codegen.py
index 89e46a5523d9..1d7d3b6d27cd 100644
--- a/src/transformers/models/codegen/modeling_codegen.py
+++ b/src/transformers/models/codegen/modeling_codegen.py
@@ -592,7 +592,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/cohere/modeling_cohere.py b/src/transformers/models/cohere/modeling_cohere.py
index 018fc3b8622c..01b5ee3b9e7a 100644
--- a/src/transformers/models/cohere/modeling_cohere.py
+++ b/src/transformers/models/cohere/modeling_cohere.py
@@ -665,7 +665,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.