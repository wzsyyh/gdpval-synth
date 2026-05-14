# Design Document: Stabilizing `let_chains` in the 2024 Edition

# Overview

This document outlines the design and rationale for stabilizing the `let_chains` feature, as proposed in PR #132833. The feature enables the `&&`-chaining of `let` statements within `if` and `while` expressions, allowing their intermixture with boolean expressions. This stabilization is targeted for the Rust 2024 edition and future editions, as described in the associated tracking issue #53667 and RFC 2497.

# Feature Description

The `let_chains` feature allows developers to write complex conditional logic more concisely by chaining `let` bindings and boolean checks in a single `if` or `while` expression. For example, the following code parses a function call string:

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
    fn exec(&self) -> Option<i32> {
        let iter = self.args.iter().copied();
        match self.fn_name {
            "sum" => Some(iter.sum()),
            "max" => iter.max(),
            "min" => iter.min(),
            _ => None,
        }
    }
}
```

The patterns within the `let` sub-expressions may be either irrefutable or refutable. The feature will be available only in the 2024 edition and future editions; users of older editions will receive an error directing them to update.

# Rationale for Edition Restriction

Rust typically ships new features to all editions. However, `let_chains` require a breaking change related to the drop order of temporaries in `if let` chains. Specifically, the compiler must generate correct MIR (Mid-level Intermediate Representation) for `if let` chains, and the current drop order in older editions creates inconsistencies between `if let` and `if true && let` patterns. This is tracked in issue #104843.

The 2024 edition introduces drop order changes (issue #124085) that shorten the lifetime of temporaries in `if let` expressions. These changes also affect `if let` chains and provide a consistent solution to the MIR generation problem. To maintain behavioral consistency and leverage the new drop order, `let_chains` are restricted to the 2024 edition and beyond.

# Parser Changes

The parser changes in this PR introduce a `LetChainsPolicy` enum to manage edition-dependent behavior. In `parse_expr_if`, the policy is set to `LetChainsPolicy::EditionDependent { current_edition: lo.edition() }`, where the edition is taken from the span of the `if` keyword. This ensures the scoping code checks the correct edition.

The `parse_expr_while` method is updated similarly, using the edition from the `while` span. The `parse_expr_cond` method now accepts a `let_chains_policy` parameter of type `LetChainsPolicy`. Inside, the `CondChecker` is initialized with this policy, replacing the previous unconditional feature gating. The `CondChecker` now uses the policy to decide whether `let` chains are permitted in the given edition, providing consistent error messages for unsupported editions.

# Rollout Strategy

As edition 2024 is new, this stabilization PR enables `let_chains` on 2024 without immediately removing the feature gate. The `let_chains` feature gate will continue to be available for a limited time (proposed: 3 months after stabilization) on older editions to allow nightly users to adopt the 2024 edition gradually. This transition period balances immediate usability for 2024 edition users with a reasonable migration path for the ecosystem.

# Conclusion

Stabilizing `let_chains` in the 2024 edition resolves long-standing ergonomic issues in conditional pattern matching while ensuring correct drop order semantics. The parser changes are minimal and edition-aware, and a brief feature gate retention period supports a smooth transition. This design enables more expressive and readable Rust code for all users of the 2024 edition.
