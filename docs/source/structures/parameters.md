# Parameters

## Setting/ Loading/ Retrieving Parameters
Both pipelines and components use the following methods.

### Setting Parameters
`set_params()` sets parameters in pipelines or components.

Example:
```python
pipeline.set_params(raw_params={
    "sub_pipeline;component:param": 2,  # Sets param in component within sub_pipeline
    "sub_pipeline:param": 3,            # Sets param in sub_pipeline
    "param": 4                          # Sets param at root level
}, base_priority=1000)
```
### Loading Parameters

`load_params()` loads parameters from files.

Example:
```python
pipeline.load_params(params_file='params.toml', placeholders_file='placeholders.toml')
```
note: 
1. both can use .py file as parameters/placeholders as well
2. By default, parameters files are indicated in gpt_graph/config/config.toml
3. You also need to set GPT_GRAPH_FOLDER in gpt_graph/config/env.toml

### Retrieving Parameters

`get_all_params()` retrieves all parameters.

Example:
```python
all_params = pipeline.get_all_params()
print(all_params)
```

## Parameter Priority
Parameters can have different priorities:

| Priority | Description |
|----------|-------------|
| 0        | Default |
| 1+       | Loading from config file|
| 1000+    | Manually set params |
| ...      | ... |

## Parameter Types
Parameters have several attributes:

1. **Type**: 
   - input
   - param
   - placeholder

2. **Status**: 
   - input
   - empty
   - default
   - assigned
   - ult_input
   - config
   - filter_cri
   - cache

3. **Value**: 
   - The actual parameter value
   - `<CACHE>`
   - `<INPUT>`
   - `<EMPTY>`

4. **priority**: 
   - 1000+ indicates a manual change, rather than a config file change or default value

5. **placeholder**: 
   - Represented as `[some thing]`


