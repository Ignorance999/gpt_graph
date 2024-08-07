# Step
Steps are executable units within a pipeline.

- They are stored in `Pipeline.sub_steps` / `sub_steps_q` during runtime.
- You can also check `sub_step_graph`, which is a StepGraph object showing the sequence of execution of Steps.
- After execution, they are moved to `sub_steps_history`.
- You can refer to [pipeline](pipeline.md) for how Steps are created.

