# PR #63209 description listing stabilized features, closed issues, and blocker checklist


# Seed Material: rust-lang/rust#63209: Stabilize `async_await` in Rust 1.39.0
Source: github_issue_pr
Identifier: pr:rust-lang/rust#63209

Repository: rust-lang/rust
PR Number: #63209
PR Title: Stabilize `async_await` in Rust 1.39.0
Merged At: 2019-08-20T22:16:08Z
Changed Files: 181
Additions: +271, Deletions: -605

## PR Description
Here we stabilize:
- free and inherent `async fn`s,
- the `<expr>.await` expression form,
- and the `async move? { ... }` block form.

Closes https://github.com/rust-lang/rust/issues/62149.
Closes https://github.com/rust-lang/rust/issues/50547.

All the blockers are now closed.

<details>

- [x] FCP in https://github.com/rust-lang/rust/issues/62149
- [x] https://github.com/rust-lang/rust/issues/61949; PR in https://github.com/rust-lang/rust/pull/62849.
- [x] https://github.com/rust-lang/rust/issues/62517; PR in https://github.com/rust-lang/rust/pull/63376.
- [x] https://github.com/rust-lang/rust/issues/63225; PR in https://github.com/rust-lang/rust/pull/63501
- [x] https://github.com/rust-lang/rust/issues/63388; PR in https://github.com/rust-lang/rust/pull/63499
- [x] https://github.com/rust-lang/rust/issues/63500; PR in https://github.com/rust-lang/rust/pull/63501
- [x] https://github.com/rust-lang/rust/issues/62121#issuecomment-506884048
    - [x] Some tests for control flow (PR https://github.com/rust-lang/rust/pull/63387):
          - `?`
          - `return` in `async` blocks
          - `break`
    - [x] https://github.com/rust-lang/rust/pull/61775#issuecomment-506883180, i.e. tests for https://github.com/rust-lang/rust/pull/60944 with `async fn`s instead). PR in https://github.com/rust-lang/rust/pull/63383

</details>

r? @cramertj 

## Diff (first 3000 chars)
diff --git a/src/librustc/error_codes.rs b/src/librustc/error_codes.rs
index b3eee7c346489..a200a058f4f99 100644
--- a/src/librustc/error_codes.rs
+++ b/src/librustc/error_codes.rs
@@ -2088,7 +2088,6 @@ generator can be constructed.
 Erroneous code example:
 
 ```edition2018,compile-fail,E0698
-#![feature(async_await)]
 async fn bar<T>() -> () {}
 
 async fn foo() {
@@ -2101,7 +2100,6 @@ To fix this you must bind `T` to a concrete type such as `String`
 so that a generator can then be constructed:
 
 ```edition2018
-#![feature(async_await)]
 async fn bar<T>() -> () {}
 
 async fn foo() {
diff --git a/src/librustc_typeck/check/mod.rs b/src/librustc_typeck/check/mod.rs
index fc1ee649e287f..9c7ac83e82e97 100644
--- a/src/librustc_typeck/check/mod.rs
+++ b/src/librustc_typeck/check/mod.rs
@@ -4197,8 +4197,6 @@ impl<'a, 'tcx> FnCtxt<'a, 'tcx> {
     /// A possible error is to forget to add `.await` when using futures:
     ///
     /// ```
-    /// #![feature(async_await)]
-    ///
     /// async fn make_u32() -> u32 {
     ///     22
     /// }
diff --git a/src/librustc_typeck/error_codes.rs b/src/librustc_typeck/error_codes.rs
index ca9ce3d22b5cb..b52183d4b1b56 100644
--- a/src/librustc_typeck/error_codes.rs
+++ b/src/librustc_typeck/error_codes.rs
@@ -4751,7 +4751,6 @@ E0733: r##"
 Recursion in an `async fn` requires boxing. For example, this will not compile:
 
 ```edition2018,compile_fail,E0733
-#![feature(async_await)]
 async fn foo(n: usize) {
     if n > 0 {
         foo(n - 1).await;
@@ -4763,12 +4762,11 @@ To achieve async recursion, the `async fn` needs to be desugared
 such that the `Future` is explicit in the return type:
 
 ```edition2018,compile_fail,E0720
-# #![feature(async_await)]
 use std::future::Future;
-fn foo_desugered(n: usize) -> impl Future<Output = ()> {
+fn foo_desugared(n: usize) -> impl Future<Output = ()> {
     async move {
         if n > 0 {
-            foo_desugered(n - 1).await;
+            foo_desugared(n - 1).await;
         }
     }
 }
@@ -4777,7 +4775,6 @@ fn foo_desugered(n: usize) -> impl Future<Output = ()> {
 Finally, the future is wrapped in a pinned box:
 
 ```edition2018
-# #![feature(async_await)]
 use std::future::Future;
 use std::pin::Pin;
 fn foo_recursive(n: usize) -> Pin<Box<dyn Future<Output = ()>>> {
diff --git a/src/libstd/keyword_docs.rs b/src/libstd/keyword_docs.rs
index f5018485ef7bc..85a9dea09ed0d 100644
--- a/src/libstd/keyword_docs.rs
+++ b/src/libstd/keyword_docs.rs
@@ -984,7 +984,6 @@ mod where_keyword { }
 
 // 2018 Edition keywords
 
-#[unstable(feature = "async_await", issue = "50547")]
 #[doc(keyword = "async")]
 //
 /// Return a [`Future`] instead of blocking the current thread.
@@ -995,7 +994,6 @@ mod where_keyword { }
 /// [not yet complete]: https://github.com/rust-lang/rust/issues/34601
 mod async_keyword { }
 
-#[unstable(feature = "async_await", issue = "50547")]
 #[doc(keyword = "await")]
 //
 /// Suspend execution until the result of a [`Future`] is ready.
diff --git a/src