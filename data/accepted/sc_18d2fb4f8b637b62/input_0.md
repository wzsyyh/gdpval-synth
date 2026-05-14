# PR #1370 diff and description from pytorch/pytorch repository


# Seed Material: pytorch/pytorch#1370: Lr scheduler
Source: github_issue_pr
Identifier: pr:pytorch/pytorch#1370

Repository: pytorch/pytorch
PR Number: #1370
PR Title: Lr scheduler
Merged At: 2017-05-25T20:21:44Z
Changed Files: 3
Additions: +478, Deletions: -1

## PR Description
Providing a unified LR scheduler.

Currently supports:
 - ReduceLROnPlateau (ported from [Keras](https://keras.io/))
 - LambdaLR
 - StepLR
 - MultiStepLR
 - ExponentialLR
 - GroupLambdaLR (Need testing)

## Diff (first 3000 chars)
diff --git a/docs/source/optim.rst b/docs/source/optim.rst
index 92e3f14d1fe54..95f5e3258495c 100644
--- a/docs/source/optim.rst
+++ b/docs/source/optim.rst
@@ -114,3 +114,21 @@ Algorithms
     :members:
 .. autoclass:: SGD
     :members:
+
+How to adjust Learning Rate
+---------------------------
+
+:mod:`torch.optim.lr_scheduler` provides several methods to adjust the learning
+rate based on the number of epoches. :class:`torch.optim.lr_scheduler.ReduceLROnPlateau`
+allows dynamic learning rate reducing based on some validation measurements.
+
+.. autoclass:: torch.optim.lr_scheduler.LambdaLR
+    :members:
+.. autoclass:: torch.optim.lr_scheduler.StepLR
+    :members:
+.. autoclass:: torch.optim.lr_scheduler.MultiStepLR
+    :members:
+.. autoclass:: torch.optim.lr_scheduler.ExponentialLR
+    :members:
+.. autoclass:: torch.optim.lr_scheduler.ReduceLROnPlateau
+    :members:
diff --git a/test/test_optim.py b/test/test_optim.py
index bff3b5a8196b0..8e43c04018169 100644
--- a/test/test_optim.py
+++ b/test/test_optim.py
@@ -4,9 +4,11 @@
 import torch
 import torch.optim as optim
 import torch.legacy.optim as old_optim
+import torch.nn.functional as F
+from torch.optim import SGD
 from torch.autograd import Variable
 from torch import sparse
-
+from torch.optim.lr_scheduler import LambdaLR, StepLR, MultiStepLR, ExponentialLR, ReduceLROnPlateau
 from common import TestCase, run_tests
 
 
@@ -392,5 +394,157 @@ def test_invalid_param_type(self):
             optim.SGD(Variable(torch.randn(5, 5)), lr=3)
 
 
+class SchedulerTestNet(torch.nn.Module):
+    def __init__(self):
+        super(SchedulerTestNet, self).__init__()
+        self.conv1 = torch.nn.Conv2d(1, 1, 1)
+        self.conv2 = torch.nn.Conv2d(1, 1, 1)
+
+    def forward(self, x):
+        return self.conv2(F.relu(self.conv1(x)))
+
+
+class TestLRScheduler(TestCase):
+    def setUp(self):
+        self.net = SchedulerTestNet()
+        self.opt = SGD(
+            [{'params': self.net.conv1.parameters()}, {'params': self.net.conv2.parameters(), 'lr': 0.5}],
+            lr=0.05)
+
+    def test_step_lr(self):
+        # lr = 0.05     if epoch < 3
+        # lr = 0.005    if 30 <= epoch < 6
+        # lr = 0.0005   if epoch >= 9
+        single_targets = [0.05] * 3 + [0.005] * 3 + [0.0005] * 3 + [0.00005] * 3
+        targets = [single_targets, list(map(lambda x: x * 10, single_targets))]
+        scheduler = StepLR(self.opt, gamma=0.1, step_size=3)
+        epochs = 10
+        self._test(scheduler, targets, epochs)
+
+    def test_multi_step_lr(self):
+        # lr = 0.05     if epoch < 2
+        # lr = 0.005    if 2 <= epoch < 5
+        # lr = 0.0005   if epoch < 9
+        # lr = 0.00005   if epoch >= 9
+        single_targets = [0.05] * 2 + [0.005] * 3 + [0.0005] * 4 + [0.00005] * 3
+        targets = [single_targets, list(map(lambda x: x * 10, single_targets))]
+        scheduler = MultiStepLR(self.opt, gamma=0.1, milestones=[2, 5, 9])
+        epochs = 10
+        self._test(sched