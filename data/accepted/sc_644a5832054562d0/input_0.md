# PR #36630 diff showing all 55 changed files with additions and deletions


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

## Diff
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
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/dbrx/modeling_dbrx.py b/src/transformers/models/dbrx/modeling_dbrx.py
index 446652894880..08f11ed6ffd4 100644
--- a/src/transformers/models/dbrx/modeling_dbrx.py
+++ b/src/transformers/models/dbrx/modeling_dbrx.py
@@ -1119,7 +1119,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/diffllama/modeling_diffllama.py b/src/transformers/models/diffllama/modeling_diffllama.py
index f490525d9994..d69dcf3b59df 100644
--- a/src/transformers/models/diffllama/modeling_diffllama.py
+++ b/src/transformers/models/diffllama/modeling_diffllama.py
@@ -904,7 +904,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/emu3/modeling_emu3.py b/src/transformers/models/emu3/modeling_emu3.py
index 8ad29c02ad56..47360222fce3 100644
--- a/src/transformers/models/emu3/modeling_emu3.py
+++ b/src/transformers/models/emu3/modeling_emu3.py
@@ -1483,7 +1483,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/gemma/modeling_gemma.py b/src/transformers/models/gemma/modeling_gemma.py
index 083052747250..807abe2b9f47 100644
--- a/src/transformers/models/gemma/modeling_gemma.py
+++ b/src/transformers/models/gemma/modeling_gemma.py
@@ -637,7 +637,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/gemma3/processing_gemma3.py b/src/transformers/models/gemma3/processing_gemma3.py
index 00cece56a269..c5492f3b7685 100644
--- a/src/transformers/models/gemma3/processing_gemma3.py
+++ b/src/transformers/models/gemma3/processing_gemma3.py
@@ -65,6 +65,7 @@ def __init__(
         self.image_seq_length = image_seq_length
         self.image_token_id = tokenizer.image_token_id
         self.boi_token = tokenizer.boi_token
+        self.image_token = tokenizer.boi_token
         image_tokens_expanded = "".join([tokenizer.image_token] * image_seq_length)
         self.full_image_sequence = f"\n\n{tokenizer.boi_token}{image_tokens_expanded}{tokenizer.eoi_token}\n\n"
 
diff --git a/src/transformers/models/glm/modeling_glm.py b/src/transformers/models/glm/modeling_glm.py
index 53f488116dae..d155beff7713 100644
--- a/src/transformers/models/glm/modeling_glm.py
+++ b/src/transformers/models/glm/modeling_glm.py
@@ -646,7 +646,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/gpt_neo/modeling_gpt_neo.py b/src/transformers/models/gpt_neo/modeling_gpt_neo.py
index e72fff18e00f..13ff3cd740df 100755
--- a/src/transformers/models/gpt_neo/modeling_gpt_neo.py
+++ b/src/transformers/models/gpt_neo/modeling_gpt_neo.py
@@ -796,7 +796,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/gpt_neox/modeling_gpt_neox.py b/src/transformers/models/gpt_neox/modeling_gpt_neox.py
index 9bbd94d798ad..97590faf705f 100755
--- a/src/transformers/models/gpt_neox/modeling_gpt_neox.py
+++ b/src/transformers/models/gpt_neox/modeling_gpt_neox.py
@@ -640,7 +640,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/gpt_neox_japanese/modeling_gpt_neox_japanese.py b/src/transformers/models/gpt_neox_japanese/modeling_gpt_neox_japanese.py
index 3e13ce09c593..aab7183ccf96 100755
--- a/src/transformers/models/gpt_neox_japanese/modeling_gpt_neox_japanese.py
+++ b/src/transformers/models/gpt_neox_japanese/modeling_gpt_neox_japanese.py
@@ -668,7 +668,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/gptj/modeling_gptj.py b/src/transformers/models/gptj/modeling_gptj.py
index 24f224ad1bb2..effaa3b72510 100644
--- a/src/transformers/models/gptj/modeling_gptj.py
+++ b/src/transformers/models/gptj/modeling_gptj.py
@@ -895,7 +895,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/granite/modeling_granite.py b/src/transformers/models/granite/modeling_granite.py
index 1822bd627d1d..e7a95c719f05 100644
--- a/src/transformers/models/granite/modeling_granite.py
+++ b/src/transformers/models/granite/modeling_granite.py
@@ -649,7 +649,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/granitemoe/modeling_granitemoe.py b/src/transformers/models/granitemoe/modeling_granitemoe.py
index 73086f958c75..192c99df7f57 100644
--- a/src/transformers/models/granitemoe/modeling_granitemoe.py
+++ b/src/transformers/models/granitemoe/modeling_granitemoe.py
@@ -1122,7 +1122,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/granitemoeshared/modeling_granitemoeshared.py b/src/transformers/models/granitemoeshared/modeling_granitemoeshared.py
index 3dc86991c731..d97620e62ba3 100644
--- a/src/transformers/models/granitemoeshared/modeling_granitemoeshared.py
+++ b/src/transformers/models/granitemoeshared/modeling_granitemoeshared.py
@@ -1067,7 +1067,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/helium/modeling_helium.py b/src/transformers/models/helium/modeling_helium.py
index c3f57149d802..40aac3b93306 100644
--- a/src/transformers/models/helium/modeling_helium.py
+++ b/src/transformers/models/helium/modeling_helium.py
@@ -633,7 +633,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/idefics/modeling_idefics.py b/src/transformers/models/idefics/modeling_idefics.py
index 3ca196936c3e..da18b35d4852 100644
--- a/src/transformers/models/idefics/modeling_idefics.py
+++ b/src/transformers/models/idefics/modeling_idefics.py
@@ -1367,7 +1367,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/jetmoe/modeling_jetmoe.py b/src/transformers/models/jetmoe/modeling_jetmoe.py
index 814c62a5fd96..9518ef0be5d3 100644
--- a/src/transformers/models/jetmoe/modeling_jetmoe.py
+++ b/src/transformers/models/jetmoe/modeling_jetmoe.py
@@ -1128,7 +1128,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/llama/modeling_llama.py b/src/transformers/models/llama/modeling_llama.py
index 159f41b3cecb..e52d4087be18 100644
--- a/src/transformers/models/llama/modeling_llama.py
+++ b/src/transformers/models/llama/modeling_llama.py
@@ -635,7 +635,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/longt5/modeling_longt5.py b/src/transformers/models/longt5/modeling_longt5.py
index 9dce31623603..70ec2db49f5a 100644
--- a/src/transformers/models/longt5/modeling_longt5.py
+++ b/src/transformers/models/longt5/modeling_longt5.py
@@ -1604,7 +1604,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/mimi/modeling_mimi.py b/src/transformers/models/mimi/modeling_mimi.py
index 8eece150cfac..4539cfd0bd34 100644
--- a/src/transformers/models/mimi/modeling_mimi.py
+++ b/src/transformers/models/mimi/modeling_mimi.py
@@ -1066,7 +1066,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/mistral/modeling_mistral.py b/src/transformers/models/mistral/modeling_mistral.py
index 4c0f6b8b6863..07a3e7ed4178 100644
--- a/src/transformers/models/mistral/modeling_mistral.py
+++ b/src/transformers/models/mistral/modeling_mistral.py
@@ -600,7 +600,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/mistral/modular_mistral.py b/src/transformers/models/mistral/modular_mistral.py
index 10337f4eef04..20f0528627d5 100644
--- a/src/transformers/models/mistral/modular_mistral.py
+++ b/src/transformers/models/mistral/modular_mistral.py
@@ -118,7 +118,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/mixtral/modeling_mixtral.py b/src/transformers/models/mixtral/modeling_mixtral.py
index 4112bed373f7..8fd3f7540ecd 100644
--- a/src/transformers/models/mixtral/modeling_mixtral.py
+++ b/src/transformers/models/mixtral/modeling_mixtral.py
@@ -734,7 +734,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/mllama/modeling_mllama.py b/src/transformers/models/mllama/modeling_mllama.py
index a86d00ed8be7..4c43d644d1c9 100644
--- a/src/transformers/models/mllama/modeling_mllama.py
+++ b/src/transformers/models/mllama/modeling_mllama.py
@@ -1082,7 +1082,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/moonshine/modeling_moonshine.py b/src/transformers/models/moonshine/modeling_moonshine.py
index 963b7e7aa25e..fc4770fd8f61 100644
--- a/src/transformers/models/moonshine/modeling_moonshine.py
+++ b/src/transformers/models/moonshine/modeling_moonshine.py
@@ -999,7 +999,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/moshi/modeling_moshi.py b/src/transformers/models/moshi/modeling_moshi.py
index 4a5f9d68a0f6..e3d63e40e32a 100644
--- a/src/transformers/models/moshi/modeling_moshi.py
+++ b/src/transformers/models/moshi/modeling_moshi.py
@@ -1296,7 +1296,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
@@ -1610,7 +1610,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/mt5/modeling_mt5.py b/src/transformers/models/mt5/modeling_mt5.py
index 9c2d23b7afbd..558b67123492 100644
--- a/src/transformers/models/mt5/modeling_mt5.py
+++ b/src/transformers/models/mt5/modeling_mt5.py
@@ -1195,7 +1195,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/nemotron/modeling_nemotron.py b/src/transformers/models/nemotron/modeling_nemotron.py
index ef73c55e0fd5..d6d77887a2a3 100644
--- a/src/transformers/models/nemotron/modeling_nemotron.py
+++ b/src/transformers/models/nemotron/modeling_nemotron.py
@@ -883,7 +883,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/olmo/modeling_olmo.py b/src/transformers/models/olmo/modeling_olmo.py
index 2f6dc1fa9c9b..626b248e2c02 100644
--- a/src/transformers/models/olmo/modeling_olmo.py
+++ b/src/transformers/models/olmo/modeling_olmo.py
@@ -611,7 +611,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/olmo2/modeling_olmo2.py b/src/transformers/models/olmo2/modeling_olmo2.py
index 05b8d1722383..101f79750e13 100644
--- a/src/transformers/models/olmo2/modeling_olmo2.py
+++ b/src/transformers/models/olmo2/modeling_olmo2.py
@@ -612,7 +612,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/opt/modeling_opt.py b/src/transformers/models/opt/modeling_opt.py
index a306e84b23a8..28134e141c9f 100644
--- a/src/transformers/models/opt/modeling_opt.py
+++ b/src/transformers/models/opt/modeling_opt.py
@@ -643,7 +643,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/paligemma/modeling_paligemma.py b/src/transformers/models/paligemma/modeling_paligemma.py
index c49e91b2820a..5d8542c1d399 100644
--- a/src/transformers/models/paligemma/modeling_paligemma.py
+++ b/src/transformers/models/paligemma/modeling_paligemma.py
@@ -340,19 +340,22 @@ def get_decoder(self):
     def _update_causal_mask(
         self,
         attention_mask,
-        token_type_ids,
-        past_key_values,
-        cache_position,
-        input_tensor,
-        is_training: bool = False,
+        token_type_ids=None,
+        past_key_values=None,
+        cache_position=None,
+        input_tensor=None,
+        is_training: bool = None,
     ):
         if self.config.text_config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and 0.0 in attention_mask:
                 return attention_mask
             return None
-
+        is_training = is_training if is_training is not None else self.training
         using_static_cache = isinstance(past_key_values, StaticCache)
         min_dtype = torch.finfo(self.dtype).min
+        if input_tensor is None:
+            input_tensor = attention_mask
+
         inputs_lead_dim, sequence_length = input_tensor.shape[:2]
         if using_static_cache:
             target_length = past_key_values.get_max_cache_shape()
@@ -387,6 +390,8 @@ def _update_causal_mask(
 
             # First unmask prefix tokens during training
             if is_training:
+                if token_type_ids is None:
+                    raise ValueError("Token type ids must be provided during training")
                 causal_mask[:, :, :, :mask_length] = causal_mask[:, :, :, :mask_length].masked_fill(
                     token_type_ids[:, None, None, :].to(causal_mask.device) == 0, 0
                 )
diff --git a/src/transformers/models/persimmon/modeling_persimmon.py b/src/transformers/models/persimmon/modeling_persimmon.py
index df6153c81185..a71169dbdda9 100644
--- a/src/transformers/models/persimmon/modeling_persimmon.py
+++ b/src/transformers/models/persimmon/modeling_persimmon.py
@@ -683,7 +683,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/phi/modeling_phi.py b/src/transformers/models/phi/modeling_phi.py
index cac12d59b00e..c273f9062836 100644
--- a/src/transformers/models/phi/modeling_phi.py
+++ b/src/transformers/models/phi/modeling_phi.py
@@ -609,7 +609,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/phi3/modeling_phi3.py b/src/transformers/models/phi3/modeling_phi3.py
index 6712f24f413e..8b49ad087670 100644
--- a/src/transformers/models/phi3/modeling_phi3.py
+++ b/src/transformers/models/phi3/modeling_phi3.py
@@ -675,7 +675,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/phimoe/modeling_phimoe.py b/src/transformers/models/phimoe/modeling_phimoe.py
index f06255030e65..66452fd943ac 100644
--- a/src/transformers/models/phimoe/modeling_phimoe.py
+++ b/src/transformers/models/phimoe/modeling_phimoe.py
@@ -1180,7 +1180,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/pix2struct/modeling_pix2struct.py b/src/transformers/models/pix2struct/modeling_pix2struct.py
index 42e190d2e44d..63c392db12f3 100644
--- a/src/transformers/models/pix2struct/modeling_pix2struct.py
+++ b/src/transformers/models/pix2struct/modeling_pix2struct.py
@@ -1591,7 +1591,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/pop2piano/modeling_pop2piano.py b/src/transformers/models/pop2piano/modeling_pop2piano.py
index 0c4a2eda9786..cadf71871eef 100644
--- a/src/transformers/models/pop2piano/modeling_pop2piano.py
+++ b/src/transformers/models/pop2piano/modeling_pop2piano.py
@@ -1004,7 +1004,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/qwen2/modeling_qwen2.py b/src/transformers/models/qwen2/modeling_qwen2.py
index 53f675192b44..d5d922e208e8 100644
--- a/src/transformers/models/qwen2/modeling_qwen2.py
+++ b/src/transformers/models/qwen2/modeling_qwen2.py
@@ -613,7 +613,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py b/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py
index a90baf246eda..fb0c8f5dbe0e 100644
--- a/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py
+++ b/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py
@@ -1246,7 +1246,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/qwen2_moe/modeling_qwen2_moe.py b/src/transformers/models/qwen2_moe/modeling_qwen2_moe.py
index 036bdb26ca56..80e215854b4a 100644
--- a/src/transformers/models/qwen2_moe/modeling_qwen2_moe.py
+++ b/src/transformers/models/qwen2_moe/modeling_qwen2_moe.py
@@ -1068,7 +1068,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/qwen2_vl/modeling_qwen2_vl.py b/src/transformers/models/qwen2_vl/modeling_qwen2_vl.py
index dfea703003db..66b780f312d7 100644
--- a/src/transformers/models/qwen2_vl/modeling_qwen2_vl.py
+++ b/src/transformers/models/qwen2_vl/modeling_qwen2_vl.py
@@ -1192,7 +1192,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/stablelm/modeling_stablelm.py b/src/transformers/models/stablelm/modeling_stablelm.py
index 4621851fea88..2f59cda241f8 100755
--- a/src/transformers/models/stablelm/modeling_stablelm.py
+++ b/src/transformers/models/stablelm/modeling_stablelm.py
@@ -938,7 +938,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/starcoder2/modeling_starcoder2.py b/src/transformers/models/starcoder2/modeling_starcoder2.py
index 0187f733abca..a23dfa9d46ba 100644
--- a/src/transformers/models/starcoder2/modeling_starcoder2.py
+++ b/src/transformers/models/starcoder2/modeling_starcoder2.py
@@ -596,7 +596,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and past_key_values is not None:
diff --git a/src/transformers/models/switch_transformers/modeling_switch_transformers.py b/src/transformers/models/switch_transformers/modeling_switch_transformers.py
index a347654a4902..73282a150926 100644
--- a/src/transformers/models/switch_transformers/modeling_switch_transformers.py
+++ b/src/transformers/models/switch_transformers/modeling_switch_transformers.py
@@ -1140,7 +1140,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/t5/modeling_t5.py b/src/transformers/models/t5/modeling_t5.py
index ba96c10ed0c7..0851c0eac95f 100644
--- a/src/transformers/models/t5/modeling_t5.py
+++ b/src/transformers/models/t5/modeling_t5.py
@@ -1209,7 +1209,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/udop/modeling_udop.py b/src/transformers/models/udop/modeling_udop.py
index 2b0e27f45e18..089434ca8273 100644
--- a/src/transformers/models/udop/modeling_udop.py
+++ b/src/transformers/models/udop/modeling_udop.py
@@ -1542,7 +1542,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/umt5/modeling_umt5.py b/src/transformers/models/umt5/modeling_umt5.py
index 7b868696f640..07c44bef7b90 100644
--- a/src/transformers/models/umt5/modeling_umt5.py
+++ b/src/transformers/models/umt5/modeling_umt5.py
@@ -852,7 +852,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/models/whisper/modeling_whisper.py b/src/transformers/models/whisper/modeling_whisper.py
index 2bcf4026a35a..dacd147c151f 100644
--- a/src/transformers/models/whisper/modeling_whisper.py
+++ b/src/transformers/models/whisper/modeling_whisper.py
@@ -1378,7 +1378,7 @@ def _update_causal_mask(
         input_tensor: torch.Tensor,
         cache_position: torch.Tensor,
         past_key_values: Cache,
-        output_attentions: bool,
+        output_attentions: bool = False,
     ):
         if self.config._attn_implementation == "flash_attention_2":
             if attention_mask is not None and (attention_mask == 0.0).any():
diff --git a/src/transformers/processing_utils.py b/src/transformers/processing_utils.py
index c85abdc739e8..4b0c2ebdd49f 100644
--- a/src/transformers/processing_utils.py
+++ b/src/transformers/processing_utils.py
@@ -1069,7 +1069,7 @@ def from_pretrained(
 
         args = cls._get_arguments_from_pretrained(pretrained_model_name_or_path, **kwargs)
         processor_dict, kwargs = cls.get_processor_dict(pretrained_model_name_or_path, **kwargs)
-
+        processor_dict.update({k: v for k, v in kwargs.items() if k in processor_dict.keys()})
         return cls.from_args_and_dict(args, processor_dict, **kwargs)
 
     @classmethod
diff --git a/src/transformers/utils/attention_visualizer.py b/src/transformers/utils/attention_visualizer.py
new file mode 100644
index 000000000000..54efdbfcdafe
--- /dev/null
+++ b/src/transformers/utils/attention_visualizer.py
@@ -0,0 +1,229 @@
+# coding=utf-8
+# Copyright 2025 The HuggingFace Inc. team.
+#
+# Licensed under the Apache License, Version 2.0 (the "License");
+# you may not use this file except in compliance with the License.
+# You may obtain a copy of the License at
+#
+#     http://www.apache.org/licenses/LICENSE-2.0
+#
+# Unless required by applicable law or agreed to in writing, software
+# distributed under the License is distributed on an "AS IS" BASIS,
+# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
+# See the License for the specific language governing permissions and
+# limitations under the License.
+
+
+import requests
+from PIL import Image
+
+from ..models.auto.auto_factory import _get_model_class
+from ..models.auto.configuration_auto import AutoConfig
+from ..models.auto.modeling_auto import MODEL_FOR_PRETRAINING_MAPPING, MODEL_MAPPING
+from ..models.auto.processing_auto import PROCESSOR_MAPPING_NAMES, AutoProcessor
+from ..models.auto.tokenization_auto import TOKENIZER_MAPPING_NAMES, AutoTokenizer
+from .import_utils import is_torch_available
+
+
+if is_torch_available():
+    import torch
+    import torch.nn as nn
+
+# Print the matrix with words as row labels
+GREEN = "\033[92m"
+YELLOW = "\033[93m"
+RESET = "\033[0m"
+BLACK_SQUARE = "■"
+WHITE_SQUARE = "⬚"
+
+
+def generate_attention_matrix_from_mask(words, mask, img_token="<img>", sliding_window=None, token_type_ids=None):
+    """
+    Generates an attention matrix from a given attention mask.
+
+    Optionally applies a sliding window mask (e.g., for Gemma2/3) and
+    marks regions where image tokens occur based on the specified `img_token`.
+    """
+    mask = mask.int()
+    if mask.ndim == 3:
+        mask = mask[0, :, :]
+    if mask.ndim == 4:
+        mask = mask[0, 0, :, :]
+
+    n = len(words)
+    max_word_length = max(len(repr(word)) for word in words)
+    first_img_idx = 0
+    output = []
+
+    for i, k in enumerate(words):
+        if k == img_token and not first_img_idx:
+            first_img_idx = i
+            mask[i, i] = 2  # Mark yellow regions
+        if first_img_idx > 0 and (k != img_token or i == n - 1):
+            if i == n - 1:
+                i += 1
+            mask[first_img_idx:i, first_img_idx:i] = 2  # Mark yellow regions
+            first_img_idx = 0
+
+    # Generate sliding window mask (size = 4), excluding img_token
+    sliding_window_mask = None
+    if sliding_window is not None:
+        sliding_window_mask = [[1 if (0 <= i - j < sliding_window) else 0 for j in range(n)] for i in range(n)]
+
+    row_dummy = " ".join(
+        f"{YELLOW}{BLACK_SQUARE}{RESET}"
+        if mask[0, j]
+        else f"{GREEN}{BLACK_SQUARE}{RESET}"
+        if 0 == j
+        else BLACK_SQUARE
+        if mask[0, j]
+        else WHITE_SQUARE
+        for j in range(n)
+    )
+
+    # Print headers
+    legend = f"{GREEN}{BLACK_SQUARE}{RESET}: i == j (diagonal)   {YELLOW}{BLACK_SQUARE}{RESET}: token_type_ids"
+    output.append(" " + legend)
+    f_string = " " * (max_word_length + 5) + "Attention Matrix".ljust(len(row_dummy) // 2)
+    if sliding_window is not None:
+        f_string += "Sliding Window Mask"
+    output.append(f_string)
+
+    vertical_header = []
+    for idx, word in enumerate(words):
+        if mask[idx, idx] == 2:
+            vertical_header.append([f"{YELLOW}{k}{RESET}" for k in list(str(idx).rjust(len(str(n))))])
+        else:
+            vertical_header.append(list(str(idx).rjust(len(str(n)))))
+
+    vertical_header = list(map(list, zip(*vertical_header)))  # Transpose
+
+    for row in vertical_header:
+        output.append(
+            (max_word_length + 5) * " " + " ".join(row) + "    |    " + " ".join(row)
+            if sliding_window is not None
+            else ""
+        )
+
+    for i, word in enumerate(words):
+        word_repr = repr(word).ljust(max_word_length)
+        colored_word = f"{YELLOW}{word_repr}{RESET}" if img_token in word else word_repr
+        row_display = " ".join(
+            f"{YELLOW}{BLACK_SQUARE}{RESET}"
+            if img_token in words[j] and mask[i, j] and img_token in words[i]
+            else f"{GREEN}{BLACK_SQUARE}{RESET}"
+            if i == j
+            else BLACK_SQUARE
+            if mask[i, j]
+            else WHITE_SQUARE
+            for j in range(n)
+        )
+        sliding_window_row = ""
+        if sliding_window is not None:
+            sliding_window_row = " ".join(
+                f"{YELLOW}{BLACK_SQUARE}{RESET}"
+                if img_token in words[j] and img_token in words[i]
+                else f"{GREEN}{BLACK_SQUARE}{RESET}"
+                if i == j
+                else BLACK_SQUARE
+                if sliding_window_mask[i][j]
+                else WHITE_SQUARE
+                for j in range(n)
+            )
+
+        output.append(f"{colored_word}: {str(i).rjust(2)} {row_display}    |    {sliding_window_row}")
+
+    return "\n".join(output)
+
+
+class AttentionMaskVisualizer:
+    def __init__(self, model_name: str):
+        config = AutoConfig.from_pretrained(model_name)
+        self.image_token = "<img>"
+        if hasattr(config.get_text_config(), "sliding_window"):
+            config.sliding_window = 5
+        try:
+            mapped_cls = _get_model_class(config, MODEL_MAPPING)
+        except Exception:
+            mapped_cls = _get_model_class(config, MODEL_FOR_PRETRAINING_MAPPING)
+
+        if mapped_cls is None:
+            raise ValueError(f"Model name {model_name} is not supported for attention visualization")
+        self.mapped_cls = mapped_cls
+
+        class _ModelWrapper(mapped_cls, nn.Module):
+            def __init__(self, config, model_name):
+                nn.Module.__init__(self)
+                self.dummy_module = nn.Linear(1, 1)
+                self.config = config
+
+        self.model = _ModelWrapper(config, model_name)
+        self.model.to(config.torch_dtype)
+        self.repo_id = model_name
+        self.config = config
+
+    def __call__(self, input_sentence: str, suffix=""):
+        self.visualize_attention_mask(input_sentence, suffix=suffix)
+
+    def visualize_attention_mask(self, input_sentence: str, suffix=""):
+        model = self.model
+        kwargs = {}
+        if self.config.model_type in PROCESSOR_MAPPING_NAMES:
+            img = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg?download=true"
+            img = Image.open(requests.get(img, stream=True).raw)
+            processor = AutoProcessor.from_pretrained(self.repo_id, image_seq_length=5)
+            if hasattr(processor, "image_token"):
+                image_token = processor.image_token
+            else:
+                image_token = processor.tokenizer.convert_ids_to_tokens([processor.image_token_id])[0]
+
+            if image_token:
+                input_sentence = input_sentence.replace("<img>", image_token)
+
+            inputs = processor(img, input_sentence, suffix=suffix, return_tensors="pt")
+
+            self.image_token = processor.tokenizer.convert_ids_to_tokens([processor.image_token_id])[0]
+
+            attention_mask = inputs["attention_mask"]
+            if "token_type_ids" in inputs:  # TODO inspect signature of update causal mask
+                kwargs["token_type_ids"] = inputs["token_type_ids"]
+            tokens = processor.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
+        elif self.config.model_type in TOKENIZER_MAPPING_NAMES:
+            tokenizer = AutoTokenizer.from_pretrained(self.repo_id)
+            tokens = tokenizer.tokenize(input_sentence)
+            attention_mask = tokenizer(input_sentence, return_tensors="pt")["attention_mask"]
+        else:
+            raise ValueError(f"Model type {model.config.model_type} does not support attention visualization")
+
+        model.config._attn_implementation = "eager"
+        model.train()
+        attention_mask = ~model._update_causal_mask(
+            attention_mask=attention_mask,
+            input_tensor=attention_mask.to(self.model.dtype),
+            cache_position=torch.arange(attention_mask.shape[1]),
+            past_key_values=None,
+            **kwargs,
+        ).bool()
+        top_bottom_border = "##" * (
+            len(f"Attention visualization for {self.config.model_type} | {self.mapped_cls}") + 4
+        )  # Box width adjusted to text length
+        side_border = "##"
+        print(f"\n{top_bottom_border}")
+        print(
+            "##"
+            + f"  Attention visualization for \033[1m{self.config.model_type}:{self.repo_id}\033[0m {self.mapped_cls.__name__}".center(
+                len(top_bottom_border)
+            )
+            + "    "
+            + side_border
+        )
+        print(f"{top_bottom_border}")
+        f_string = generate_attention_matrix_from_mask(
+            tokens,
+            attention_mask,
+            img_token=self.image_token,
+            sliding_window=getattr(self.config, "sliding_window", None),
+            token_type_ids=kwargs.get("token_type_ids", None),
+        )
+        print(f_string)
+        print(f"{top_bottom_border}")
