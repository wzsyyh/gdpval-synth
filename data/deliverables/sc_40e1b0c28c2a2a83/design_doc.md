# Design Doc - Stabilize let_chains in Rust 2024 Edition

## Overview

This design document describes the stabilization of the `let_chains` feature as proposed in [RFC 2497](https://github.com/rust-lang/rfcs/pull/2497) and tracked in [issue #53667](https://github.com/rust-lang/rust/issues/53667). The feature enables chaining of `let` statements using `&&` inside `if` and `while` expressions, allowing seamless intermixture with boolean expressions. The patterns inside the `let` sub-expressions may be either irrefutable or refutable.

The stabilization is scoped exclusively to the [2024 edition](https://doc.rust-lang.org/nightly/edition-guide/rust-2024/index.html) and future editions. Users on older editions will receive a compiler error with a hint to update their edition. This restriction is driven by drop-order concerns that are resolved by edition 2024 changes, as detailed in the sections below.

The following example, taken from the stabilization report in PR #132833, demonstrates how let chains enable concise parsing logic that would otherwise require nested `if let` blocks or early returns:

```rust
struct FnCall<'a> {
    fn_name: &'a str,
    args: Vec<i32>,
}

fn is_legal_ident(s: &str) -> bool {
    s.chars()
        .all(|c| ('a'..='z').contains(&c) || ('A'..='Z').contains(&c))
}

impl<'a> FnCall<'a> {
    fn parse(s: &'a str) -> Option<Self> {
        if let Some((fn_name, after_name)) = s.split_once("(")
            && !fn_name.is_empty()
            && is_legal_ident(fn_name)
            && let Some((args_str, "")) = after_name.rsplit_once(")")
        {
            let args = args_str
                .split(',')
                .map(|arg| arg.parse())
                .collect::<Result<Vec<_>, _>>();
            args.ok().map(|args| FnCall { fn_name, args })
        } else {
            None
        }
    }
}
```

## Motivation

Prior to let chains, developers who needed to perform multiple pattern matches and boolean checks in sequence were forced into one of two unsatisfying patterns: deeply nested `if let` blocks or a series of early returns using `let ... else`. Both approaches add visual noise and reduce readability, particularly when the logic is inherently sequential and linear.

The `FnCall::parse` example from the stabilization report illustrates this clearly. Without let chains, the function would require either four levels of nested `if let` blocks or a sequence of `let ... else` statements with explicit `return None`. With let chains, the entire validation pipeline — splitting on `(`, checking the function name is non-empty, verifying it is a legal identifier, and splitting on `)` — reads as a single, flat, left-to-right chain of conditions.

This pattern is common in parsing code, validation logic, and any context where a series of fallible operations must be performed in sequence with short-circuit evaluation. Stabilizing let chains eliminates a significant source of boilerplate in idiomatic Rust code.

## Edition Restriction Rationale

Rust's general policy is to ship new features to all editions, including the oldest. However, some features require a breaking change so significant that offering the feature without the breaking change is impractical. This has precedent: the `async`/`await` syntax introduced in the 2018 edition required `async` and `await` to become keywords, which was only possible at an edition boundary.

For let chains, the critical issue is the **drop order of temporaries in `if let` chains**. As documented in [issue #104843](https://github.com/rust-lang/rust/issues/104843), generating correct MIR (Mid-level Intermediate Representation) for `if let` chains is problematic under the pre-2024 drop order. If `if let` chains were stabilized on older editions, the compiler would produce MIR with incorrect or inconsistent drop semantics for temporaries created within the chain conditions.

Consistency with existing `if let` behavior is a core requirement. As discussed in [PR #103293](https://github.com/rust-lang/rust/pull/103293#issuecomment-1293408574), it would be unacceptable for `if let ... {}` and `if true && let ... {}` to exhibit different drop behavior. The semantics of chained `let` expressions must be identical to those of a single `if let` expression.

Edition 2024 introduces [drop order changes](https://github.com/rust-lang/rust/issues/124085) that shorten the lifetime of temporaries in `if let` expressions. These changes are sensible in their own right — they align temporary lifetimes with programmer expectations — but they also solve the MIR generation problem for let chains. Because the new drop order is required for correct let-chain behavior, the feature must be gated to edition 2024 and later.

## Compiler Implementation Details

The core parsing changes are concentrated in `compiler/rustc_parse/src/parser/expr.rs`. The implementation introduces a `LetChainsPolicy` enum with an `EditionDependent` variant that carries the current edition of the enclosing `if` or `while` expression. This policy is threaded through the parser to ensure edition-aware gating.

In `parse_expr_if`, the edition is extracted from the span of the `if` keyword token (`lo.edition()`) and passed as a `LetChainsPolicy::EditionDependent` value to `parse_expr_cond`:
```rust
fn parse_expr_if(&mut self) -> PResult<'a, P<Expr>> {
    let lo = self.prev_token.span;
    let let_chains_policy = LetChainsPolicy::EditionDependent {
        current_edition: lo.edition()
    };
    let cond = self.parse_expr_cond(let_chains_policy)?;
    self.parse_if_after_cond(lo, cond)
}
```

A parallel change is made in `parse_expr_while`, which constructs the same `LetChainsPolicy::EditionDependent` value using the `while` token's span edition:
```rust
fn parse_expr_while(&mut self, opt_label: Option<Label>, lo: Span) -> PResult<'a, P<Expr>> {
    let policy = LetChainsPolicy::EditionDependent {
        current_edition: lo.edition()
    };
    // ...
}
```

The `parse_expr_cond` method signature is updated to accept a `let_chains_policy: LetChainsPolicy` parameter. This is a public method, as it is used by rustfmt forks for custom `if` expression handling. The method creates a `CondChecker` with the policy and visits the condition expression:
```rust
pub fn parse_expr_cond(&mut self, let_chains_policy: LetChainsPolicy) -> PResult<'a, P<Expr>> {
    let attrs = self.parse_outer_attributes()?;
    let (mut cond, _) = self.parse_expr_res(
        Restrictions::NO_STRUCT_LITERAL | Restrictions::ALLOW_LET,
        attrs,
    )?;
    CondChecker::new(self, let_chains_policy).visit_expr(&mut cond);
    Ok(cond)
}
```

The previous implementation called `self.psess.gated_spans.ungate_last(sym::let_chains, cond.span)` to remove feature gating for stable `let` expressions. This logic is removed as part of the stabilization, since `let` in conditions is now always permitted on edition 2024. The `CondChecker` itself handles the edition check, emitting an appropriate error when let chains are used on editions prior to 2024.

## Transition Plan

As edition 2024 is very new, the stabilization approach is designed to minimize disruption. The stabilization PR does not immediately remove the `let_chains` feature gate; rather, it makes let chains available without the feature gate on edition 2024, while keeping the feature gate active on older editions.

The proposal is to continue offering the `let_chains` feature gate on older editions for a limited transition period of approximately 3 months after stabilization. This gives nightly users who have been relying on let chains time to migrate their codebases to the 2024 edition without being abruptly broken.

After the transition period, the feature gate on older editions will be removed, and let chains will be exclusively available on edition 2024 and later. The exact timeline will be communicated through the Rust blog and the edition migration guide.

## References

- [RFC 2497 — Let chains in `if` and `while`](https://github.com/rust-lang/rfcs/pull/2497)
- [Tracking issue #53667 — `let_chains` feature](https://github.com/rust-lang/rust/issues/53667)
- [Issue #104843 — MIR generation for let chains](https://github.com/rust-lang/rust/issues/104843)
- [PR #103293 — Consistency discussion for `if let` drop behavior](https://github.com/rust-lang/rust/pull/103293#issuecomment-1293408574)
- [Issue #124085 — Drop order changes in edition 2024](https://github.com/rust-lang/rust/issues/124085)
- [Edition Guide — Rust 2024](https://doc.rust-lang.org/nightly/edition-guide/rust-2024/index.html)
- [PR #132833 — Stabilize `let_chains` in the 2024 edition](https://github.com/rust-lang/rust/pull/132833)
