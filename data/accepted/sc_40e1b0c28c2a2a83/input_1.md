# Links to tracking issue #53667, RFC 2497, edition guide, issue #104843, PR #103293 comment, and issue #124085


# Seed Material: rust-lang/rust#132833: Stabilize let chains in the 2024 edition
Source: github_issue_pr
Identifier: pr:rust-lang/rust#132833

Repository: rust-lang/rust
PR Number: #132833
PR Title: Stabilize let chains in the 2024 edition
Merged At: 2025-04-22T11:04:49Z
Changed Files: 46
Additions: +411, Deletions: -184

## PR Description
# Stabilization report

This proposes the stabilization of `let_chains` ([tracking issue], [RFC 2497]) in the [2024 edition] of Rust.

[tracking issue]: https://github.com/rust-lang/rust/issues/53667
[RFC 2497]: https://github.com/rust-lang/rfcs/pull/2497
[2024 edition]: https://doc.rust-lang.org/nightly/edition-guide/rust-2024/index.html

## What is being stabilized

The ability to `&&`-chain `let` statements inside `if` and `while` is being stabilized, allowing intermixture with boolean expressions. The patterns inside the `let` sub-expressions can be irrefutable or refutable.

```Rust
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

fn main() {
    println!("{:?}", FnCall::parse("sum(1,2,3)").unwrap().exec());
    println!("{:?}", FnCall::parse("max(4,5)").unwrap().exec());
}
```

The feature will only be stabilized for the 2024 edition and future editions. Users of past editions will get an error with a hint to update the edition.

closes rust-lang/rust#53667

## Why 2024 edition?

Rust generally tries to ship new features to all editions. So even the oldest editions receive the newest features. However, sometimes a feature requires a breaking change so much that offering the feature without the breaking change makes no sense. This occurs rarely, but has happened in the 2018 edition already with `async` and `await` syntax. It required an edition boundary in order for `async`/`await` to become keywords, and the entire feature foots on those keywords.

In the instance of let chains, the issue is the drop order of `if let` chains. If we want `if let` chains to be compatible with `if let`, drop order makes it hard for us to [generate correct MIR]. It would be strange to have different behaviour for `if let ... {}` and `if true && let ... {}`. So it's better to [stay consistent with `if let`].

In edition 2024, [drop order changes] have been introduced to make `if let` temporaries be lived more shortly. These changes also affected `if let` chains. These changes make sense even if you don't take the `if let` chains MIR generation problem into account. But if we want to use them as the solution to the MIR generation problem, we need to restrict let chains to edition 2024 and beyond: for let chains, it's not just a change towards more sensible behaviour, but one required for correct function.

[generate correct MIR]: https://github.com/rust-lang/rust/issues/104843
[stay consistent with `if let`]: https://github.com/rust-lang/rust/pull/103293#issuecomment-1293408574
[drop order changes]: https://github.com/rust-lang/rust/issues/124085

## Introduction considerations

As edition 2024 is very new, this stabilization PR only makes it possible to use let chains on 2024 without that feature gate, it doesn't mark that feature gate as stable/removed. I would propose to continue offering the `let_chains` feature (behind a feature gate) for a limited time (maybe 3 months after stabilization?) on older editions to allow nightly users to adopt editi

## Diff (first 3000 chars)
diff --git a/compiler/rustc_parse/src/parser/expr.rs b/compiler/rustc_parse/src/parser/expr.rs
index df44b3cc23c86..20a5252624d55 100644
--- a/compiler/rustc_parse/src/parser/expr.rs
+++ b/compiler/rustc_parse/src/parser/expr.rs
@@ -26,6 +26,7 @@ use rustc_macros::Subdiagnostic;
 use rustc_session::errors::{ExprParenthesesNeeded, report_lit_error};
 use rustc_session::lint::BuiltinLintDiag;
 use rustc_session::lint::builtin::BREAK_WITH_LABEL_AND_LOOP;
+use rustc_span::edition::Edition;
 use rustc_span::source_map::{self, Spanned};
 use rustc_span::{BytePos, ErrorGuaranteed, Ident, Pos, Span, Symbol, kw, sym};
 use thin_vec::{ThinVec, thin_vec};
@@ -2605,7 +2606,10 @@ impl<'a> Parser<'a> {
     /// Parses an `if` expression (`if` token already eaten).
     fn parse_expr_if(&mut self) -> PResult<'a, P<Expr>> {
         let lo = self.prev_token.span;
-        let cond = self.parse_expr_cond()?;
+        // Scoping code checks the top level edition of the `if`; let's match it here.
+        // The `CondChecker` also checks the edition of the `let` itself, just to make sure.
+        let let_chains_policy = LetChainsPolicy::EditionDependent { current_edition: lo.edition() };
+        let cond = self.parse_expr_cond(let_chains_policy)?;
         self.parse_if_after_cond(lo, cond)
     }
 
@@ -2714,18 +2718,17 @@ impl<'a> Parser<'a> {
     }
 
     /// Parses the condition of a `if` or `while` expression.
+    ///
+    /// The specified `edition` in `let_chains_policy` should be that of the whole `if` construct,
+    /// i.e. the same span we use to later decide whether the drop behaviour should be that of
+    /// edition `..=2021` or that of `2024..`.
     // Public because it is used in rustfmt forks such as https://github.com/tucant/rustfmt/blob/30c83df9e1db10007bdd16dafce8a86b404329b2/src/parse/macros/html.rs#L57 for custom if expressions.
-    pub fn parse_expr_cond(&mut self) -> PResult<'a, P<Expr>> {
+    pub fn parse_expr_cond(&mut self, let_chains_policy: LetChainsPolicy) -> PResult<'a, P<Expr>> {
         let attrs = self.parse_outer_attributes()?;
         let (mut cond, _) =
             self.parse_expr_res(Restrictions::NO_STRUCT_LITERAL | Restrictions::ALLOW_LET, attrs)?;
 
-        CondChecker::new(self).visit_expr(&mut cond);
-
-        if let ExprKind::Let(_, _, _, Recovered::No) = cond.kind {
-            // Remove the last feature gating of a `let` expression since it's stable.
-            self.psess.gated_spans.ungate_last(sym::let_chains, cond.span);
-        }
+        CondChecker::new(self, let_chains_policy).visit_expr(&mut cond);
 
         Ok(cond)
     }
@@ -3020,7 +3023,8 @@ impl<'a> Parser<'a> {
 
     /// Parses a `while` or `while let` expression (`while` token already eaten).
     fn parse_expr_while(&mut self, opt_label: Option<Label>, lo: Span) -> PResult<'a, P<Expr>> {
-        let cond = self.parse_expr_cond().map_err(|mut err| {
+        let policy = LetChainsPolicy::EditionDependent { current_edition: lo.edition()