# Pipeline

## Overview

The Pipeline class is a core component of the gpt_graph framework, inheriting from Component, which in turn inherits from Closure. It's designed to orchestrate the execution of multiple components in a structured and flexible manner.

## Key Features

1. **Component Connection**: Uses the `|` operator to connect components sequentially.
2. **Component Addition**: Uses the `+` operator to add components for potential linkings or bindings.
3. **Execution Management**: The `Pipeline.run` method orchestrates the execution flow.

## Creating a Pipeline

1. **Subclass Pipeline**: 
   ```python
   class CustomPipeline(Pipeline):
       ...
   ```

2. **Initialize Components**:
   ```python
   def __init__(self, **kwargs):
       super().__init__(**kwargs)
       self.component1 = Component1()
       self.component2 = Component2()
       ...
   ```

3. **Define Pipeline Structure**:
   ```python
   (self | self.component1 | self.component2) + [
       self.additional_component1,
       self.additional_component2,
       ...
   ]
   ```

4. **Implement Custom Method**:
   ```python
   # the following are Component, but Component.category == "method"
   @component()
   def custom_method(self):
       ...
   ```

5. **Configure Parameters**:
   ```python
   self.set_params(...)
   self.set_placeholders(...)
   ```

## Example: ReadBook Pipeline (tutorial 6)

The ReadBook pipeline demonstrates:

- Initializing various components (Filter, YouTubeLister, PDFSplitter, etc.)
- Connecting main flow components with `|`
- Adding potential components with `+`
- Implementing custom routing and data processing methods
- Configuring output paths and placeholders

The pipeline structure allows for dynamic execution paths, where components like `pdf_splitter` or `youtube_lister` can be activated based on input type or other conditions.

## Execution Process

The `run` method manages the execution:
1. Passes data through main flow components
2. Checks for linkings and bindings at each step. Components satisfy the criteria will create Steps and put into Pipeline.sub_steps_q as priority queue. Usually, Steps create by calling Pipeline.route_to (including those triggered by Component.linkings) inside the Pipeline will have a higher priority than Steps created by Component.bindings.
3. Produces final output

For more details on advanced features and execution, refer to the tutorials and `Pipeline.run` method documentation.

