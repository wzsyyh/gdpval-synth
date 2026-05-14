# Design Document: Stabilization of `#![feature(min_const_generics)]`

# Overview

This design document details the stabilization of the `#![feature(min_const_generics)]` feature in Rust version 1.51. This feature introduces the ability to parameterize functions, type aliases, types, traits, and implementations by constants, in addition to the existing parameters by types and lifetimes. The stabilization is based on the subset of full const generics described in RFC #2000 and targets release 1.51, with the beta release scheduled for 2021-02-11 and the stable release for 2021-03-25.

The feature was tracked under issue #74878 and is implemented by PR #79135. It provides a foundational capability that allows for more expressive generic programming in Rust, particularly for scenarios involving arrays and other value-parameterized types.

# Scope and Syntax

The scope of `min_const_generics` is intentionally limited to ensure a stable and well-understood initial feature set. Const parameters are permitted in all locations where types and lifetimes are supported. The syntax for declaring a const parameter is `const IDENT: Type`.

Currently, the allowed types for const parameters are restricted to integers, `char`, and `bool`. Generic const arguments are not permitted to involve computations that depend on generic parameters. This means that when instantiating a const parameter, only the following are allowed: (1) const expressions that do not depend on any generic parameters (e.g., `{ foo() + 1 }` where `foo` is a `const fn`), or (2) standalone const parameters (e.g., `{N}`).

# Motivation

The primary motivation for const generics is Rust's built-in array type, which is parametric over a constant. Without const generics, implementing traits for arrays of different lengths was cumbersome; the standard library previously only contained trait implementations for arrays up to a length of 32. This restriction has been lifted using const generics.

Const parameters allow users to specify variants of generic types more naturally parameterized by values rather than types. This enables the replacement of many uses of the `typenum` crate with native const parameters, which improves compilation time, code readability, and diagnostics. The subset defined by `min_const_generics` is self-contained, extensive enough to address the most frequent use cases, and extends naturally to full `const_generics` once remaining design questions are resolved.

# Example Walkthrough

The following example, from the stabilization report, demonstrates key aspects of `min_const_generics`.

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

**Trait and Struct Definitions:** The `Foo` trait is generic over a constant `N` of type `usize`. Its `method` function is further generic over a constant `M`. The `Bar` struct is generic over a type `T` and a constant `N`, storing an array `[T; N]`.

**Implementation Block:** The `impl` block implements `Foo<N>` for `Bar<u8, N>`. The method body performs a bitwise AND operation across nested arrays, showcasing how const generics allow for type-safe, dimension-checked operations.

**Function:** The standalone `function<const N: u16>()` uses the const parameter `N` directly in arithmetic expressions, demonstrating that const parameters are usable as values within function bodies.

**Usage in `main`:** A `Bar` instance is created with `inner: [0xff; 3]`, fixing `N=3`. Calling `bar.method(...)` infers `M` from the 2-element arrays passed as arguments. The `assert_eq!` verifies the bitwise AND results. Finally, `function::<17>()` explicitly specifies `N=17`, and the assertion checks the calculated value 153.

# Limitations

The initial stabilization of `min_const_generics` includes several important limitations designed to manage complexity and ensure stability. These limitations are as follows:

1.  **Parameter Types:** Only `usize`, `bool`, and `char` are permitted as types for const parameters.
2.  **Generic Argument Restrictions:** Generic const arguments are not allowed to involve computations that depend on other generic parameters.
3.  **Permitted Instantiations:** Const parameters may only be instantiated using either: (a) const expressions that do not depend on any generic parameters (e.g., `{ foo() + 1 }` where `foo` is a `const fn`), or (b) standalone const parameters (e.g., `{N}`).

These constraints are explicitly defined in the stabilization report to limit the feature's surface area. The subset is designed to be self-contained and sufficient for the most common use cases, such as implementing traits for arrays, while leaving a clear path for extension to full `const_generics` in the future.

# References

The following references are foundational to the `min_const_generics` feature:

*   **PR #79135**: 'stabilize `#![feature(min_const_generics)]` in 1.51'. This pull request contains the stabilization report and implementation.
*   **Tracking Issue #74878**: The primary tracking issue for the `min_const_generics` feature.
*   **RFC #2000**: The original RFC proposing the const generics feature, which `min_const_generics` is based upon.
