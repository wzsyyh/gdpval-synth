# PR description and diff for pydantic/pydantic#2721 (merged 2021-09-06), including the changelog entry, documentation screenshots, and the new VS Code integration guide


# Seed Material: pydantic/pydantic#2721: ✨ Add autocomplete support for VS Code, via `dataclass_transform`
Source: github_issue_pr
Identifier: pr:pydantic/pydantic#2721

Repository: pydantic/pydantic
PR Number: #2721
PR Title: ✨ Add autocomplete support for VS Code, via `dataclass_transform`
Merged At: 2021-09-06T10:13:02Z
Changed Files: 13
Additions: +303, Deletions: -17

## PR Description
<!-- Thank you for your contribution! -->
<!-- Unless your change is trivial, please create an issue to discuss the change before creating a PR -->
<!-- See https://pydantic-docs.helpmanual.io/contributing/ for help on Contributing -->

## Change Summary

<!-- Please give a short summary of the changes. -->

In short, this adds ✨ autocomplete ✨ for fields when creating a new instance of a Pydantic model. 🎉

![Selection_408](https://user-images.githubusercontent.com/1326112/116777149-255de600-aa6d-11eb-84b7-e978951d2266.png)

### Details

Eric Traut, Pyright's author, is writing a proposal for a new standard for Python `typing` to help declare models like *pydantic* and others as dataclass-like, to support autocompletion when creating a new instance (automatic typed `__init__` constructor).

The gist is that a new decorator `typing.dataclass_transform()` that would be applied in *pydantic*'s metaclass (not needed by final users) would give it those extra powers.

The draft standard is here: https://github.com/microsoft/pyright/blob/master/specs/dataclass_transforms.md

The discussion is here: https://github.com/microsoft/pyright/discussions/1782

The draft includes a small trick to adopt it right away even before the standard is accepted, adding a custom minimal `__dataclass_transform__` to the codebase. Pyright, and so, Pylance, and so VS Code, **already support it**.

So, this simple change in this PR enables autocompletion in VS Code right away. In a similar way that it is provided in PyCharm by @koxudaxi's awesome plug-in.

As a side note, if this standard is accepted, I think it would also replace and/or simplify a large part of the *pydantic* mypy plugin.

Thanks @koxudaxi for pointing me to this in the discussions! https://github.com/samuelcolvin/pydantic/discussions/2698

## Related issue number

I understand Samuel was already aware this was in progress and already in comm with Eric, so I'm not sure this justifies an issue. If so, let me know and I'll make one.

<!-- Are there any issues opened that will be resolved by merging this change? -->

## Checklist

* [ ] Unit tests for the changes exist
* [x] Tests pass on CI and coverage remains at 100%
* [x] Documentation reflects the changes where applicable
* [x] `changes/<pull request or issue id>-<github username>.md` file added describing change
  (see [changes/README.md](https://github.com/samuelcolvin/pydantic/blob/master/changes/README.md) for details)


## Diff (first 3000 chars)
diff --git a/changes/2721-tiangolo.md b/changes/2721-tiangolo.md
new file mode 100644
index 00000000000..a64f9c18d84
--- /dev/null
+++ b/changes/2721-tiangolo.md
@@ -0,0 +1 @@
+Add support for autocomplete in VS Code via `__dataclass_transform__`
diff --git a/docs/img/vs_code_01.png b/docs/img/vs_code_01.png
new file mode 100644
index 00000000000..24920c79381
Binary files /dev/null and b/docs/img/vs_code_01.png differ
diff --git a/docs/img/vs_code_02.png b/docs/img/vs_code_02.png
new file mode 100644
index 00000000000..c78536be6b9
Binary files /dev/null and b/docs/img/vs_code_02.png differ
diff --git a/docs/img/vs_code_03.png b/docs/img/vs_code_03.png
new file mode 100644
index 00000000000..85a7eb9b2d8
Binary files /dev/null and b/docs/img/vs_code_03.png differ
diff --git a/docs/img/vs_code_04.png b/docs/img/vs_code_04.png
new file mode 100644
index 00000000000..77bf2e529c4
Binary files /dev/null and b/docs/img/vs_code_04.png differ
diff --git a/docs/img/vs_code_05.png b/docs/img/vs_code_05.png
new file mode 100644
index 00000000000..b5feb9fef02
Binary files /dev/null and b/docs/img/vs_code_05.png differ
diff --git a/docs/img/vs_code_06.png b/docs/img/vs_code_06.png
new file mode 100644
index 00000000000..af4dc48fb8e
Binary files /dev/null and b/docs/img/vs_code_06.png differ
diff --git a/docs/img/vs_code_07.png b/docs/img/vs_code_07.png
new file mode 100644
index 00000000000..eec492586d9
Binary files /dev/null and b/docs/img/vs_code_07.png differ
diff --git a/docs/img/vs_code_08.png b/docs/img/vs_code_08.png
new file mode 100644
index 00000000000..1e21af90feb
Binary files /dev/null and b/docs/img/vs_code_08.png differ
diff --git a/docs/visual_studio_code.md b/docs/visual_studio_code.md
new file mode 100644
index 00000000000..98c58fb01f4
--- /dev/null
+++ b/docs/visual_studio_code.md
@@ -0,0 +1,269 @@
+*pydantic* works well with any editor or IDE out of the box because it's made on top of standard Python type annotations.
+
+When using [Visual Studio Code (VS Code)](https://code.visualstudio.com/), there are some **additional editor features** supported, comparable to the ones provided by the [PyCharm plugin](./pycharm_plugin.md).
+
+This means that you will have **autocompletion** (or "IntelliSense") and **error checks** for types and required arguments even while creating new *pydantic* model instances.
+
+![pydantic autocompletion in VS Code](./img/vs_code_01.png)
+
+## Configure VS Code
+
+To take advantage of these features, you need to make sure you configure VS Code correctly, using the recommended settings.
+
+In case you have a different configuration, here's a short overview of the steps.
+
+### Install Pylance
+
+You should use the [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) extension for VS Code. It is the recommended, next-generation, official VS Code plug-in for Python.
+
+Pylance is installed as part of the [Python Extension for VS Code](https://marketplace.visualstudio.com/items?itemName