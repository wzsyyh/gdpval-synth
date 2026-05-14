# Code Review: PR #7928 - Remove Sort Requirement from pad_sequence

# Code Review: PR #7928 - Remove Sort Requirement from pad_sequence

Code Review: PR #7928 - Remove Sort Requirement from pad_sequence

## Summary

This review covers PR #7928, titled 'remove sort requirement from pad-sequence', which was merged on 2018-05-30T20:36:56Z. The PR picks up from #5974 and addresses the comments from that earlier pull request.

The changes affect two files: `torch/nn/utils/rnn.py` and `test/test_nn.py`. The diff shows +20 additions and -23 deletions, indicating a net simplification of the codebase.

The primary objective of this PR is to remove the requirement that input sequences to `pad_sequence` must be sorted. This improves the function's usability by allowing users to pass sequences in any order.

## Code Changes Analysis

The changes to `torch/nn/utils/rnn.py` are minimal but impactful. The diff shows modifications starting at line 274 of the file.

The documentation string has been updated. The original docstring contained a requirement about sorting, which has been removed. The new docstring describes that `pad_sequence` stacks a list of Tensors along a new dimension and pads them to equal length, without mentioning a sort requirement.

The function signature `pad_sequence(sequences, batch_first=False, padding_value=0)` remains unchanged. No new parameters were added or removed.

The key change is the removal of code that enforced the sort requirement. This simplifies the function and allows it to process sequences in any order, whether sorted or unsorted.

## Test Changes Analysis

The test changes in `test/test_nn.py` are more extensive and demonstrate thorough validation of the new behavior.

For single dimensional sequences, the tests now use tensors `a = torch.tensor([1, 2, 3])`, `b = torch.tensor([4, 5])`, and `c = torch.tensor([6])`. The test order has been changed to `[b, a, c]` instead of `[a, b, c]` to test unsorted input.

The expected output for `batch_first = true` with unsorted input is `torch.tensor([[4, 5, 0], [1, 2, 3], [6, 0, 0]])`. This verifies that the padding occurs correctly regardless of input order.

A new test case has been added: 'Test pad sorted sequence'. This uses the original sorted order `[a, b, c]` with expected output `torch.tensor([[1, 2, 3], [4, 5, 0], [6, 0, 0]])`, ensuring backward compatibility.

The test for padding with a non-zero value (1) now expects `torch.tensor([[4, 5, 1], [1, 2, 3], [6, 1, 1]])` for the unsorted input `[b, a, c]`.

For multi-dimensional sequences, the generation loop has changed from `for i in range(maxlen, 0, -1)` to `for i in range(1, maxlen + 1)`. This now generates sequences in increasing length order. Additionally, `random.shuffle(sequences)` has been added to randomize the order, testing unsorted input for dimensions 0, 1, 2, and 3.

The most critical test change is the removal of the `self.assertRaises(ValueError, lambda: rnn_utils.pad_sequence([b, a, c], [2, 3, 1]))` assertion. This confirms that the function no longer raises an exception for unsorted sequences.

The `pad` helper function remains unchanged. All tests now verify that the function works correctly with both sorted and unsorted inputs.

## Overall Assessment

Overall, PR #7928 successfully addresses the original issue of removing the sort requirement from `pad_sequence`. The implementation is clean and straightforward, with minimal code changes that have a significant positive impact on usability.

The PR maintains backward compatibility. The addition of the explicit test for sorted sequences ensures that existing code relying on sorted input will continue to work correctly. The function signature remains unchanged, so no API breaking changes are introduced.

The code changes follow PyTorch coding standards. The documentation update is appropriate, though it could be more explicit about the removed requirement. The test changes are comprehensive, covering both unsorted and sorted inputs across multiple dimensions.

The implementation is efficient. Removing the sort check eliminates a potential performance bottleneck for users with pre-unsorted sequences, as they no longer need to sort their data before calling the function.

The test coverage is excellent. The changes include specific tests for unsorted input order, verification of padding values, and multi-dimensional sequences with randomization. The removal of the `assertRaises(ValueError)` test is correct and necessary.

## Recommendations

Based on the review, the PR is of high quality and ready for production. However, I have a few minor suggestions for improvement.

First, the documentation update could be more explicit. The docstring should clearly state that the sort requirement has been removed, perhaps by adding a note like: 'Note: Sequences do not need to be sorted.' This would improve clarity for users reading the documentation.

Second, while the tests are comprehensive, there is one potential edge case not explicitly tested: empty sequences. The function should handle a list containing empty tensors gracefully. Adding a test case with an empty sequence would increase robustness.

Third, consider adding a performance note in the documentation. Since sorting is no longer required, users can save preprocessing time if their sequences are not naturally sorted.

Overall, I rate this PR as **Approve**. The changes are well-implemented, thoroughly tested, and address the original issue effectively. The suggestions above are minor and non-blocking.
