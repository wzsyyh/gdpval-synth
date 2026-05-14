# Design Doc - Learning Rate Scheduler Framework

# Design Doc - Learning Rate Scheduler Framework

## Overview

The learning rate scheduler framework introduced in PR #1370 provides a unified interface for adjusting learning rates during neural network training. This framework, housed in the `torch.optim.lr_scheduler` module, enables practitioners to systematically modify the learning rate across training epochs without manual intervention. The primary goal is to offer standard learning rate scheduling strategies that are commonly used in deep learning, improving convergence behavior and final model performance.

The PR introduces six scheduler implementations: `ReduceLROnPlateau`, `LambdaLR`, `StepLR`, `MultiStepLR`, `ExponentialLR`, and `GroupLambdaLR`. Each scheduler follows a consistent API pattern, allowing users to attach a scheduler to an optimizer and call `scheduler.step()` after each epoch. The `ReduceLROnPlateau` scheduler is notable as it was ported from the Keras framework and supports dynamic adjustment based on validation metrics rather than a fixed epoch schedule.

## Architecture

Schedulers are designed to work in conjunction with PyTorch optimizers. They modify the learning rate of parameter groups within an optimizer. A scheduler is initialized with an optimizer instance and, optionally, configuration parameters such as `gamma` or `milestones`. At each training step, the user calls `scheduler.step()`, which updates the `lr` attribute of each parameter group in the attached optimizer.

The test code demonstrates this interaction through a helper neural network `SchedulerTestNet` defined in `test/test_optim.py`. This network consists of two convolutional layers (`conv1` and `conv2`). The corresponding optimizer is set up with two distinct parameter groups, as shown in the `setUp` method of `TestLRScheduler`:

```python
self.opt = SGD(
    [{'params': self.net.conv1.parameters()}, {'params': self.net.conv2.parameters(), 'lr': 0.5}],
    lr=0.05)
```

Here, `conv1` parameters inherit the base learning rate of 0.05, while `conv2` parameters have a custom learning rate of 0.5. This setup tests that schedulers correctly apply differential learning rates across parameter groups, which is essential for techniques like fine-tuning where different layers may require different learning rates.

## Scheduler Catalog

The framework includes six schedulers, each implementing a distinct learning rate adjustment strategy:

- **ReduceLROnPlateau**: Adjusts the learning rate when a metric (e.g., validation loss) has stopped improving. This scheduler was ported from the Keras framework.

- **LambdaLR**: Adjusts the learning rate by multiplying it by a user-defined function that takes the epoch number as input.

- **StepLR**: Decays the learning rate by a multiplicative factor (`gamma`) every `step_size` epochs.

- **MultiStepLR**: Decays the learning rate by `gamma` at each milestone epoch specified in a list.

- **ExponentialLR**: Decays the learning rate by `gamma` every epoch, following an exponential decay schedule.

- **GroupLambdaLR**: Provides lambda-based learning rate adjustment at the parameter group level. As noted in the PR description, this scheduler requires further testing.

## Testing Strategy

The testing approach is centered around the `TestLRScheduler` class in `test/test_optim.py`. Tests use a consistent helper network and optimizer setup to validate scheduler behavior. The `SchedulerTestNet` is a simple neural network with two convolutional layers (`conv1` and `conv2`), each having a single input and output channel with kernel size 1. This simple architecture allows for clear testing of learning rate schedules without complex model dependencies.

The `setUp` method initializes the network and creates an SGD optimizer with two parameter groups. The first group uses the default learning rate (0.05), while the second group (for `conv2` parameters) explicitly sets the learning rate to 0.5. This dual-rate setup verifies that schedulers correctly handle heterogeneous learning rates across parameter groups, which is a common scenario in practice.

Each scheduler test (e.g., `test_step_lr`, `test_multi_step_lr`) computes expected learning rate targets over a series of epochs. For example, in `test_step_lr`, the expected targets for a single parameter group are: `[0.05]*3 + [0.005]*3 + [0.0005]*3 + [0.00005]*3` over 12 epochs. The targets for the second parameter group are scaled by a factor of 10 (i.e., `list(map(lambda x: x * 10, single_targets))`). The `_test` method then runs the scheduler and optimizer through the specified number of epochs, asserting that the actual learning rates match these predefined targets.

## Documentation Integration

The schedulers are integrated into PyTorch's official documentation via the `docs/source/optim.rst` file. A new section titled "How to adjust Learning Rate" is added after the existing "Algorithms" section. This section provides a brief explanation that `torch.optim.lr_scheduler` offers methods for adjusting learning rates based on epochs, with `ReduceLROnPlateau` supporting dynamic adjustment based on validation measurements.

Each scheduler is documented using Sphinx's `autoclass` directive, which automatically generates API documentation from the class docstrings. The directives are:

```rst
.. autoclass:: torch.optim.lr_scheduler.LambdaLR
    :members:
.. autoclass:: torch.optim.lr_scheduler.StepLR
    :members:
.. autoclass:: torch.optim.lr_scheduler.MultiStepLR
    :members:
.. autoclass:: torch.optim.lr_scheduler.ExponentialLR
    :members:
.. autoclass:: torch.optim.lr_scheduler.ReduceLROnPlateau
    :members:
```

This integration ensures that users can discover and understand the scheduler APIs through the standard PyTorch documentation portal, maintaining consistency with other optimizer-related components.
