# The PR description and diff for facebook/react#22114, which contains the rationale for removing the warning and the specific code changes across 4 files


# Seed Material: facebook/react#22114: Remove the warning for setState on unmounted components
Source: github_issue_pr
Identifier: pr:facebook/react#22114

Repository: facebook/react
PR Number: #22114
PR Title: Remove the warning for setState on unmounted components
Merged At: 2021-08-18T20:50:02Z
Changed Files: 4
Additions: +12, Deletions: -291

## PR Description
We have a warning that fires when you `setState` on an unmounted components. This is a proposal to remove it.

### Why was this warning added?

The warning states that it protects against memory leaks. The original use case (rewritten to Hooks) goes like this:

```js
useEffect(() => {
  function handleChange() {
     setState(store.getState())
  }
  store.subscribe(handleChange)
  return () => store.unsubscribe(handleChange)
}, [])
```

If you forget the `unsubscribe` call, after the component unmounts you'll get a memory leak. So we warn you if you set state after unmounting because we think you might've forgotten to do that.

### Why does this warning create problems?

The problem is that in practice, there's usually a much more common case in the user code:

```js
async function handleSubmit() {
  setPending(true)
  await post('/someapi') // component might unmount while we're waiting
  setPending(false)
}
```

This will trigger the `setState` warning. However, there is no actual problem here. There's no "memory leak" here: the POST comes back, we try to set state, the component is unmounted (so nothing happens), and then we're done. Nothing keeps holding onto the component indefinitely.

### Avoiding false positives is too difficult

So effectively the above case is a false positive but that's the most common one people try to solve. Even the "canonical" solution to this is pretty clumsy:

```js
let isMountedRef = useRef(false)
useEffect(() => {
  isMountedRef.current = true
  return () => {
    isMountedRef.current = false
  }
}, [])

async function handleSubmit() {
  setPending(true)
  await post('/someapi')
  if (isMountedRef.current) {
    setPending(false)
  }
}
```

It's unfortunate because we're adding slightly more runtime overhead, slightly more code, and making the code slightly less readable — all to avoid an effectively false positive warning.

Bu there are other issues, too.

In the future, we'd like to offer a feature that lets you preserve DOM and state even when the component is not visible, but disconnect its effects. With this feature, the code above doesn't work well. You'll "miss" the `setPending(false)` call because `isMountedRef.current` is `false` while the component is in a hidden tab. So once you return to the hidden tab and make it visible again, it will look as if your mutation hasn't "come through". By trying to evade the warning, we've made the behavior worse.

In addition, we've seen that this warning pushes people towards moving mutations (like POST) into effects just because effects offer an easy way to "ignore" something using the cleanup function and a flag. However, this *also* usually makes the code worse. The user action is associated with a particular event — not with the component being displayed — and so moving this code into effect introduces extra fragility. Such as the risk of the effect re-firing when some related data changes. So the warning against a problematic pattern ends up pushing people towards _more_ problematic patterns though the original code was actually fine.

### Could we not remove this?

We could make the warning less aggressive. For example, `console.warn` instead of `console.error`. However, as long as it shows up, the institutional knowledge will push people towards using a ref or moving it to an effect, and neither is desirable.

We could make add some threshold to the warning. Such as only firing it after N setStates or M seconds. However, it's hard to find one-size-fit-all heuristics, and it's probably going to be confusing either way.

In practice, direct subscriptions in components are not that common anymore. Especially now that we have custom Hooks. They tend to be concentrated in libraries, which eventually would likely move to `useMutableSource` where appropriate anyway.

So the proposal is to stop compromising the common product case, and not warn at all.

## Diff (first 3000 chars)
diff --git a/packages/react-dom/src/__tests__/ReactCompositeComponent-test.js b/packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
index 1c02667d7bc9..d4eec830da3a 100644
--- a/packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
+++ b/packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
@@ -307,7 +307,7 @@ describe('ReactCompositeComponent', () => {
     ReactDOM.render(<MyComponent />, container2);
   });
 
-  it('should warn about `forceUpdate` on unmounted components', () => {
+  it('should not warn about `forceUpdate` on unmounted components', () => {
     const container = document.createElement('div');
     document.body.appendChild(container);
 
@@ -325,19 +325,11 @@ describe('ReactCompositeComponent', () => {
 
     ReactDOM.unmountComponentAtNode(container);
 
-    expect(() => instance.forceUpdate()).toErrorDev(
-      "Warning: Can't perform a React state update on an unmounted " +
-        'component. This is a no-op, but it indicates a memory leak in your ' +
-        'application. To fix, cancel all subscriptions and asynchronous ' +
-        'tasks in the componentWillUnmount method.\n' +
-        '    in Component (at **)',
-    );
-
-    // No additional warning should be recorded
+    instance.forceUpdate();
     instance.forceUpdate();
   });
 
-  it('should warn about `setState` on unmounted components', () => {
+  it('should not warn about `setState` on unmounted components', () => {
     const container = document.createElement('div');
     document.body.appendChild(container);
 
@@ -365,22 +357,10 @@ describe('ReactCompositeComponent', () => {
     expect(renders).toBe(1);
 
     instance.setState({value: 1});
-
     expect(renders).toBe(2);
 
     ReactDOM.render(<div />, container);
-
-    expect(() => {
-      instance.setState({value: 2});
-    }).toErrorDev(
-      "Warning: Can't perform a React state update on an unmounted " +
-        'component. This is a no-op, but it indicates a memory leak in your ' +
-        'application. To fix, cancel all subscriptions and asynchronous ' +
-        'tasks in the componentWillUnmount method.\n' +
-        '    in Component (at **)\n' +
-        '    in span',
-    );
-
+    instance.setState({value: 2});
     expect(renders).toBe(2);
   });
 
diff --git a/packages/react-reconciler/src/ReactFiberWorkLoop.new.js b/packages/react-reconciler/src/ReactFiberWorkLoop.new.js
index 065d17fcc753..7797448a82e9 100644
--- a/packages/react-reconciler/src/ReactFiberWorkLoop.new.js
+++ b/packages/react-reconciler/src/ReactFiberWorkLoop.new.js
@@ -12,7 +12,6 @@ import type {Fiber, FiberRoot} from './ReactInternalTypes';
 import type {Lanes, Lane} from './ReactFiberLane.new';
 import type {SuspenseState} from './ReactFiberSuspenseComponent.new';
 import type {StackCursor} from './ReactFiberStack.new';
-import type {FunctionComponentUpdateQueue} from './ReactFiberHooks.new';
 import type {Flags} from './ReactFiberFlags';
 
 import {
@@ -53,10 +52,6 @@ imp