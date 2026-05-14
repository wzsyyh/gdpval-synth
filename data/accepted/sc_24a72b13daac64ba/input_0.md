# PR #79135 stabilization report text, including summary, motivation, example code, and in-progress in-depth description


# Seed Material: rust-lang/rust#79135: stabilize `#![feature(min_const_generics)]` in 1.51
Source: github_issue_pr
Identifier: pr:rust-lang/rust#79135

Repository: rust-lang/rust
PR Number: #79135
PR Title: stabilize `#![feature(min_const_generics)]` in 1.51
Merged At: 2020-12-27T09:55:59Z
Changed Files: 478
Additions: +699, Deletions: -1118

## PR Description
*A new Kind*
*A Sort long Prophesized*
*Once Fragile, now Eternal*

# Stabilization report

This is the stabilization report for `#![feature(min_const_generics)]` (tracking issue #74878), a subset of `#![feature(const_generics)]` (tracking issue #44580), based on rust-lang/rfcs#2000.

The [version target](https://forge.rust-lang.org/#current-release-versions) is ~~1.50 (2020-12-31 => beta, 2021-02-11 => stable)~~ 1.51 (2021-02-11 => beta, 2021-03-25 => stable).

This report is a collaborative effort of @varkor, @shepmaster and @lcnr.

## Summary

It is currently possible to parameterize functions, type aliases, types, traits and implementations by types and lifetimes.
With `#![feature(min_const_generics)]`, it becomes possible, in addition, to parameterize these by constants.

This is done using the syntax `const IDENT: Type` in the parameter listing. Unlike full const generics, `min_const_generics` is limited to parameterization by integers, and constants of type `char` or `bool`.

We already use `#![feature(min_const_generics)]` on stable to implement many common traits for arrays. See [the documentation](https://doc.rust-lang.org/nightly/std/primitive.array.html) for specific examples.

Generic const arguments, for now, are not permitted to involve computations depending on generic parameters. This means that const parameters may only be instantiated using either:

1. const expressions that do not depend on any generic parameters, e.g. `{ foo() + 1 }`, where `foo` is a `const fn`
1. standalone const parameters, e.g. `{N}`

### Example

```rust
#![feature(min_const_generics)]

trait Foo<const N: usize> {
    fn method<const M: usize>(&mut self, arr: [[u8; M]; N]);
}

struct Bar<T, const N: usize> {
    inner: [T; N],
}

impl<const N: usize> Foo<N> for Bar<u8, N> {
    fn method<const M: usize>(&mut self, arr: [[u8; M]; N]) {
        for (elem, s) in self.inner.iter_mut().zip(arr.iter()) {
            for &x in s {
                *elem &= x;
            }
        }
    }
}

fn function<const N: u16>() -> u16 {
    // Const parameters can be used freely inside of functions.
    (N + 1) / 2 * N
}

fn main() {
    let mut bar = Bar { inner: [0xff; 3] };
    // This infers the value of `M` from the type of the function argument.
    bar.method([[0b11_00, 0b01_00], [0b00_11, 0b00_01], [0b11_00, 0b00_11]]);
    assert_eq!(bar.inner, [0b01_00, 0b00_01, 0b00_00]);

    // You can also explicitly specify the value of `N`.
    assert_eq!(function::<17>(), 153);
}
```

## Motivation

Rust has the built-in array type, which is parametric over a constant. Without const generics, this type can be quite cumbersome to use as it is not possible to generically implement a trait for arrays of different lengths. For example, this meant that, for a long time, the standard library only contained trait implementations for arrays up to a length of 32. This restriction has since been lifted through the use of const generics.

Const parameters allow users to naturally specify variants of a generic type which are more naturally parameterized by values, rather than by types. For example, using const generics, many of the uses of the crate [typenum](https://crates.io/crates/typenum) may now be replaced with const parameters, improving compilation time as well as code readability and diagnostics.

The subset described by `min_const_generics` is self-contained, but extensive enough to help with the most frequent issues: implementing traits for arrays and using arbitrarily-sized arrays inside of other types. Furthermore, it extends naturally to full `const_generics` once the remaining design and implementation questions have been resolved.

## In-depth feature description

### Declaring const parameters

*Const parameters* are allowed in all places where types and lifetimes are supported. They use the syntax `const IDENT: Type`. Currently, const parameters must be declared after l