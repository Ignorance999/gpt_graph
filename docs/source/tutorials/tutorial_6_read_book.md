# Tutorial 6: ReadBook Pipeline

Note: You can refer to `gpt_graph/pipelines/read_book.py` for the complete code.

This tutorial introduces the `ReadBook` class, which extends the `Pipeline` class from the `gpt_graph` library. It's designed to process various types of input (files, URLs) and perform operations like text extraction, summarization, and text-to-speech conversion.

## Setup Instructions

To run this pipeline, you need to set up the following:

1. Rename `config/pipelines/read_book.demo.toml` to `config/pipelines/read_book.toml`
2. Rename `config/env.demo.toml` to `env.toml`, and modify the file paths as needed
3. Install extra Python libraries by referring to `requirements.txt`

## Imports

The code imports various components and utilities from the `gpt_graph` library, including:

- WebScraper, TextExtractor, TextToSpeech, GoogleDriveUploader
- YouTubeLister, DirFileLister, PDFSplitter, Summarizer
- PDFBookmarkSplitter, Filter, Saver
- Pipeline, component decorator, and other utility functions

## ReadBook Class

### Initialization

Important notes:
1. You can delete `self.tts` and `self.google_drive` if you haven't set up these components yet.
2. For testing purposes (without calling a real LLM), you can set the model name as "test" for "summarizer:model_name" (This means that summarizer's model_name parameter should be set to 'test').

The `ReadBook` class initializes various components needed for the pipeline, including:

- WebScraper
- TextExtractor
- TextToSpeech (optional)
- GoogleDriveUploader (optional)
- YouTubeLister
- DirFileLister
- PDFSplitter
- Summarizer
- PDFBookmarkSplitter
- Filter
- Saver

Each component is initialized with specific parameters and configurations. The pipeline is set up to handle different types of inputs and perform various operations on the text data.

```python
class ReadBook(Pipeline):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filter = Filter()
        self.youtube_lister = YouTubeLister()
        self.dir_file_lister = DirFileLister()
        self.pdf_splitter = PDFSplitter()
        self.summarizer = Summarizer()
        self.saver = Saver()
        self.webscraper = WebScraper()
        self.text_extract = TextExtractor()
        self.tts = TextToSpeech()
        self.google_drive = GoogleDriveUploader()

        self.router = self.router()
        self.set_data = self.set_data()

        (
            self
            | self.router
            | self.filter
            | self.summarizer
            | self.saver
            | self.tts
            | self.google_drive
        ) + [
            self.set_data,  # router
            self.pdf_splitter,  # router
            self.dir_file_lister,  # router
            self.youtube_lister,  # router
            self.webscraper,  # router
            self.text_extract,  # router
        ]

        drive_folder_path = f"{self.__class__.__name__}/{datetime.date.today()}"
        output_folder = os.path.join(
            os.environ.get("OUTPUT_FOLDER"),
            self.__class__.__name__,
            f"{datetime.date.today()}",
        )
        self.set_params({"output_folder": output_folder})
        self.set_placeholders(
            {
                "[OUTPUT_FOLDER]": output_folder,
                "[DRIVE_FOLDER_PATH]": drive_folder_path,
            }
        )
```

1. Pipeline Connections (|)
   - The | operator means a pipeline connection to the next Component.
   - Example: `self | self.router ...`
   - When processing |:
     - The UUID of the former Component is put into the latter's bindings.
   - During Pipeline.run:
     - After running each Step, each Component's bindings are checked.
     - If Component.bindings are satisfied, the Component creates a Step.
     - This Step is then put into the Pipeline's sub_steps_q.

2. Adding Components to Pipeline (+)
   - When a Component is added (+) to the Pipeline:
     - It will not run automatically after the previous Step.
     - It is just added into Pipeline.contains list
   - Possible triggering mechanisms:
     - Other Steps can "route_to" the Component to create a step.
     - Components may have special bindings attributes that trigger at specific times.
     - Other Component's linkings attributes may point to such Components.

3. Placeholder Logic
   - It's possible to set params as [xxx].
   - This indicates that it is a placeholder.
   - Later, you can set placeholders to plug in real values at once for all placeholders.


### Router Component

The `router` method determines the appropriate processing steps based on the input type:
```python
@component()
def router(self):
    nodes = self.sub_node_graph.default_get_input_nodes()

    if all(validate_nodes(nodes, type_hint="file_path")):
        # Check if all file paths are directories (indicative of folders)
        if all(os.path.isdir(node["content"]) for node in nodes):
            target_step = ["dir_file_lister", "text_extract"]  # , "step_filter"]

        # Check if all file paths end with '.pdf'
        elif all(node["content"].endswith(".pdf") for node in nodes):
            target_step = ["pdf_splitter"]
        else:
            target_step = ["text_extract"]

    elif all(validate_nodes(nodes, type_hint=HttpUrl)):
        # Check if any URL is a YouTube playlist or channel
        if any(
            "youtube.com/playlist?list=" in node["content"]
            or "youtube.com/channel/" in node["content"]
            for node in nodes
        ):
            target_step = ["youtube_lister"]
        else:
            target_step = ["webscrape"]
    else:
        target_step = "continue"

    if target_step != "continue":
        target_step.append("set_data")
        self.route_to(target_step)
        print(f"route_to: {target_step}")
```
```
```
using @component inside the Pipeline class is treated in a special way. As you can see the input of such Component is "self". When running the Pipeline, router will not be bound to self at first. It will be transformed into a Component using @. But after it has created Steps, and when such Step is run, "self" will be plugged into the function as Pipeline itself. Therefore, router can use any methods available for the Pipeline, including self.route_to, which will create Steps for the Component with specific base_name.


### Set Data Component

```python

    @component()
    def set_data(self, filter_cri=None):
        nodes = self.sub_node_graph.default_get_input_nodes(filter_cri)

        last_step_names = [s.base_name for s in self.sub_steps_history]
        last_step_name = last_step_names[-1]
        for i, node in enumerate(nodes):
            if (
                "dir_file_lister" in last_step_names
                and last_step_name == "text_extract"
            ):
                title_node = self.sub_node_graph.default_get_input_nodes(
                    filter_cri={"step_name": {"$regex": "dir_file_lister"}},
                    children=node,
                )[0]
                content = node["content"]
                title = f'{i:03}_{title_node["content"]}'

            elif last_step_name == "youtube_lister":
                content = node["content"]
                title = f'{node["extra"]["id"]:03}_{node["extra"]["title"]}'

            elif last_step_name == "webscrape":
                content = node["content"]
                title = f'{i:03}_{node["content"][:50]}'

            elif last_step_name == "text_extract":
                content = node["content"]
                file_path = node["extra"].get("output_file_path") or content[:20]
                title = f"{i:03}_{file_path}"

            elif last_step_name == "pdf_splitter":
                title = f'{i:03}_{node["extra"]["title"]}'
                content = node["content"]
            else:
                raise

            self.sub_node_graph.add_node(
                content=content,
                type=str,
                name="data",
                parent_nodes=node,
                extra={"title": title, "relative_id": i},
            )

        return
```
The above function simply try to create nodes for later usage.


## Main Execution
```python
s = ReadBook(if_load_env=True)
test_folder = os.environ.get("TEST_FOLDER")
file_path = os.path.join(test_folder, r"inputs\what_is_the_singularity_full.txt")
result = s.run(
    input_data=file_path,
    params={
        "summarizer:model_name": "test",#"chat_gpt4o_mini",
    },
)
```

So what is actually happening to the example?
```python
 self
| self.router
| self.filter
| self.summarizer
| self.saver
| self.tts
| self.google_drive

```
first you can check s.contains after the run (now i have comment out tts/ google drive for fasting process)
```
s.contains
Out[41]: 
[<InputInitializer(full_name=ReadBook;InputInitializer, base_name=InputInitializer, name=InputInitializer, uuid = 2679)>,
 <DerivedComponent(full_name=ReadBook;router.0, base_name=router, name=router.0, uuid = 2724)>,
 <Filter(full_name=ReadBook;filter.0, base_name=filter, name=filter.0, uuid = 2730)>,
 <Summarizer(full_name=ReadBook;summarizer.0, base_name=summarizer, name=summarizer.0, uuid = 2736)>,
 <Saver(full_name=ReadBook;saver.0, base_name=saver, name=saver.0, uuid = 2741)>,
 <DerivedComponent(full_name=ReadBook;set_data.0, base_name=set_data, name=set_data.0, uuid = 2746)>,
 <PDFSplitter(full_name=ReadBook;pdf_splitter.0, base_name=pdf_splitter, name=pdf_splitter.0, uuid = 2751)>,
 <DirFileLister(full_name=ReadBook;dir_file_lister.0, base_name=dir_file_lister, name=dir_file_lister.0, uuid = 2756)>,
 <YouTubeLister(full_name=ReadBook;youtube_lister.0, base_name=youtube_lister, name=youtube_lister.0, uuid = 2761)>,
 <WebScraper(full_name=ReadBook;webscraper.0, base_name=webscraper, name=webscraper.0, uuid = 2766)>,
 <TextExtractor(full_name=ReadBook;text_extract.0, base_name=text_extract, name=text_extract.0, uuid = 2771)>]
```
The above shows that all the | or + Components have been successfully included.

Next check s.sub_steps_history
```
s.sub_steps_history
Out[42]: 
[<Step(full_name=ReadBook;InputInitializer:sp0, name=InputInitializer:sp0), uuid = 2772>,
 <Step(full_name=ReadBook;router.0:sp0, name=router.0:sp0), uuid = 2779>,
 <Step(full_name=ReadBook;text_extract.0:sp0, name=text_extract.0:sp0), uuid = 2780>,
 <Step(full_name=ReadBook;set_data.0:sp0, name=set_data.0:sp0), uuid = 2781>,
 <Step(full_name=ReadBook;filter.0:sp0, name=filter.0:sp0), uuid = 2782>,
 <Step(full_name=ReadBook;summarizer.0:sp0, name=summarizer.0:sp0), uuid = 2798>,
 <Step(full_name=ReadBook;saver.0:sp0, name=saver.0:sp0), uuid = 2824>]
```
This is the actual Steps that are runned. First, we input file_path, then router is runned. It is identified as a text, so self.route_to text_extract. After handling that, it also route to set_data as well. After that, the ad-hoc Components finished running, we go back to the original chain, which is self.filter. And then we use llm to summarize the Component. Finally we save the txt. 

So where is the text saved? we can check read_book.toml:
```toml
[ReadBook.saver]
output_folder = "[OUTPUT_FOLDER]"
if_order = true    
'<UPDATE_INPUT_SCHEMA>' = {"title" = {'filter_cri' = {"step_name" = {'$regex' = "filter", '$order' = -1}},'field' = 'extra.title'}}
```
As you can see the output_folder is the placeholder [OUTPUT_FOLDER], and we have set this in ReadBook code, 
```python
self.set_placeholders(
    {
        "[OUTPUT_FOLDER]": output_folder,
        "[DRIVE_FOLDER_PATH]": drive_folder_path,
    }
```
you should find a file named 0_000_What is The Singular.txt in that folder.

One more thing, you can update Component.input_schema in config files using the special keywords <UPDATE_INPUT_SCHEMA>
