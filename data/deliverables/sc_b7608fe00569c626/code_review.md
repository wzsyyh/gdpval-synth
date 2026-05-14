# Code Review: PR #5688 - Upgrade to chardet 4.x

# Code Review: PR #5688 - Upgrade to chardet 4.x

## Summary

PR #5688 updates the requests library to support chardet 4.x by modifying two files: `requests/__init__.py` and `setup.py`. The change expands the accepted chardet version range from `>=3.0.2,<4` to `>=3.0.2,<5` in the package dependency, and updates the runtime compatibility check accordingly. The PR author states that chardet 4.0.0 is fully backward compatible with chardet 3.x for standard usage. This review finds the changes correct and recommends approval.

## Analysis of Changes

### setup.py Dependency Change

In `setup.py`, the chardet dependency constraint changes from `'chardet>=3.0.2,<4'` to `'chardet>=3.0.2,<5'`. This is a single-line change on line 45 of the file that broadens the accepted version range to include any chardet release from 3.0.2 up to but not including 5.0.0. This aligns with the PR author's claim that chardet 4.x is backward compatible.

### requests/__init__.py Compatibility Check

The `check_compatibility` function in `requests/__init__.py` previously used three separate assert statements to validate the chardet version:

```python
# chardet >= 3.0.2, < 3.1.0
assert major == 3
assert minor < 1
assert patch >= 2
```

This enforced the range chardet >= 3.0.2 and < 3.1.0, restricting to the 3.0.x series specifically. The new code replaces these with a single tuple comparison:

```python
# chardet >= 3.0.2, < 5.0.0
assert (3, 0, 2) <= (major, minor, patch) < (5, 0, 0)
```

This is both more concise and more correct. The tuple comparison leverages Python's native lexicographic ordering, which correctly compares major, then minor, then patch versions. The new range accepts chardet versions from 3.0.2 through any 4.x release, matching the `setup.py` constraint. Note that the old logic was narrower than the `setup.py` constraint at the time (it restricted to 3.0.x only, while setup.py allowed any 3.x). The new code is internally consistent between the two files.

## Risk Assessment

The primary risk is whether chardet 4.x is truly backward compatible as claimed. The PR author, who is the chardet maintainer, explicitly states that chardet 4.0.0 is 'faster and fully backward compatible with chardet 3.x (as long as you aren't mucking around in the models it uses under-the-hood directly).' Since requests only uses chardet's public API for character encoding detection, this risk is low.

The version parsing logic using `chardet_version.split('.')[:3]` handles standard version strings correctly. The tuple comparison `(3, 0, 2) <= (major, minor, patch) < (5, 0, 0)` is robust and Pythonic. One minor consideration: the upper bound of `<5` in setup.py and `<5.0.0` in the assertion are consistent, though the assertion code provides finer-grained control if needed.

The PR author notes that the next major release targeting Python 3.6+ is unlikely to come soon, given it took three years for this release. Setting the upper bound at <5 provides reasonable future-proofing without overcommitting to a distant major version.

## Recommendation

This PR should be **approved**. The changes are minimal, correct, and well-justified. The expanded version range in `setup.py` properly allows chardet 4.x while maintaining the lower bound of 3.0.2. The updated assertion in `requests/__init__.py` is not only correct but an improvement in code clarity over the original three-statement approach, using Python's native tuple comparison for clean version range checking. The backward compatibility claim from the chardet maintainer is credible given that requests uses only the public detection API. The changes in both files are consistent with each other, with the setup.py constraint and the runtime check covering the same version range of >=3.0.2, <5.0.0.
