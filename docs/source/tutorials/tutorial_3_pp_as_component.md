# tutorial 3 Pipelines contained in another Pipelines
Pipelines can be contained in other Pipelines.

Note: you can refer to test/test_pipeline.py -> test_3_pipeline_with_group()

## Pipeline Structure

```python
s3 = Session()
s3.f4 = f4()
s3.f6 = f6()
s3.f5 = f5()
g = Group(
    filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
    parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
)
s3.p6 = s3.f4 | s3.f6 | s3.f5.prepend(g)
s3.p3 = s3.p6 | s3.p6
```

`s3.p3` is a pipeline that runs `p6` twice in sequence.


## Initial Input
The initial input to `s3.p3` is `10`.

## First p6 Execution (p3;p6.0)

1. **InputInitializer**: Passes 10 to the next step.
2. **f4**: 
   - Calculates: 10 + 1 + 1 = 12, 10 - 1 + 2 = 11
   - Outputs: [12, 11]
3. **f6**: 
   - For 12: [12, 12-1, 12-2] = [12, 11, 10]
   - For 11: [11, 11-3, 11-4] = [11, 8, 7]
   - Outputs: [12, 11, 10, 11, 8, 7]
4. **f5**: 
   - Sums the two groups: sum([12, 11, 10]) = 33, sum([11, 8, 7]) = 26
   - Outputs: [33, 26]

## Second p6 Execution (p3;p6.1)

1. **InputInitializer**: Receives [33, 26] from the first p6 execution.
2. **f4**: 
   - For 33: 33 + 1 + 3 = 37, 33 - 1 + 4 = 36
   - For 26: 26 + 1 + 5 = 32, 26 - 1 + 6 = 31
   - Outputs: [37, 36, 32, 31]
3. **f6**:
   - For 37: [37, 37-5, 37-6] = [37, 32, 31]
   - For 36: [36, 36-7, 36-8] = [36, 29, 28]
   - For 32: [32, 32-9, 32-10] = [32, 23, 22]
   - For 31: [31, 31-11, 31-12] = [31, 20, 19]
   - Outputs: [37, 32, 31, 36, 29, 28, 32, 23, 22, 31, 20, 19]
4. **f5**:
   - Sums the four groups:
     sum([37, 32, 31]) = 100
     sum([36, 29, 28]) = 93
     sum([32, 23, 22]) = 77
     sum([31, 20, 19]) = 70
   - Final output: [100, 93, 77, 70]

## Final Result

The final output of `s3.p3.run(input_data=10)` is `[100, 93, 77, 70]`.


