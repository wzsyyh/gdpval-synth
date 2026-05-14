# CHICKEN Function - Technical Design Document

# CHICKEN Function - Technical Design Document

## Overview

The CHICKEN function is a new scalar string function added to ES|QL by PR #140645. Its purpose is to wrap any provided text message in ASCII art of a chicken, with the message appearing in a speech bubble above the chicken graphic. The function accepts a single argument: the keyword or text message to be displayed.

The function supports two invocation syntaxes. The primary syntax is the standard function call: `CHICKEN("Hello from ES|QL!")`. An alternative syntax uses the emoji function driven pattern: `🐔`("Hello from ES|QL!"). Both forms produce identical output, allowing users to choose their preferred style.

## Implementation Details

The core implementation is contained in the generated class `ChickenEvaluator`, located at `x-pack/plugin/esql/src/main/generated/org/elasticsearch/xpack/esql/expression/function/scalar/string/ChickenEvaluator.java`. The class is annotated as generated, with a comment indicating that edits should be made to the `EvaluatorImplementer` template instead.

ChickenEvaluator implements the `EvalOperator.ExpressionEvaluator` interface. Its constructor accepts six parameters: a `Source` object for error reporting, a `BreakingBytesRefBuilder` for building the output string, an `EvalOperator.ExpressionEvaluator` for the input message, a `ChickenArtBuilder` for the chicken rendering style, an `int width` parameter, and a `DriverContext` for execution context. The class also includes a `Warnings` field for handling runtime warnings.

The implementation relies on Lucene's `BytesRef` for byte-level string handling and Elasticsearch's compute data structures, including `Block`, `BytesRefBlock`, `BytesRefVector`, and `Page` for efficient columnar processing. The `eval(Page page)` method is the main evaluation entry point, processing input pages and producing output blocks.

## Usage Examples

The following ES|QL query uses the standard function syntax:
```
ROW CHICKEN("Hello from ES|QL!")
```

The same result can be achieved with the emoji syntax:
```
ROW `🐔`("Hello from ES|QL!")
```

Both queries produce the following ASCII art output:
```
 ____________________
< Hello from ES|QL! >
 --------------------
         \
          \__//
          /.\../.\
          \ \/ /
       '__/    \
        \-      )
         \_____/
      _____|_|____
           " "
```

## Future Considerations

The PR description notes that prior to this implementation, various flavors of a "chicken" feature were discussed in hallway conversations, Slack threads, and design documents. Ideas that were considered but not implemented in this PR include chicken-based joins and poultry-powered predicates. These remain potential areas for future exploration.
