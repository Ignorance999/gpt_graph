# Debugging Tips

There are numerous functions available for debugging purposes. After running the example in Tutorial 1, you can use the following methods:

## Cache and Component Inspection

```python
s.p6.cache  # Check cache
s.p6.contains  # Check contained Components
s.p6.get_all_params()  # Get all params recursively
```

## Graph Visualization

```python
s.p6.sub_node_graph.plot(if_pyvis=True)  # Plot node graph using pyvis
s.p6.sub_step_graph.plot(if_pyvis=True)  # Plot step graph using pyvis
# Note: For fewer steps, you can also use if_pyvis=False
```

## Component and Step Analysis

```python
s.p6.get_all_cps()  # Get all components recursively (useful for nested pipelines)
uuid_ex.show_objects()  # Show all declared objects with uuid_ex class instances in a graph
                        # Note: This class method will be removed in future formal versions
s.p6.contains[0].steps  # Access steps this way
s.p6.sub_steps_history  # View previously run Steps
```

## Data Saving and Review

```python
s.p6.save_elements  # Save elements like nodes or other attributes
                    # Review them in more detail using JSON format
```

