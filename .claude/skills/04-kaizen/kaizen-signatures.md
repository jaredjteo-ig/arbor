# Kaizen Signature Programming

Complete guide to signature-based programming with InputField and OutputField for type-safe AI agent I/O.

## What are Signatures?

Signatures define structured input/output contracts for AI agents, ensuring type-safe data flow.

```python
from kailash_kaizen import Signature, InputField, OutputField

# Define a signature
sig = Signature(
    name="Summarize",
    inputs=[
        InputField("text", "str", description="Text to summarize"),
        InputField("max_length", "int", description="Maximum summary length", default=100),
    ],
    outputs=[
        OutputField("summary", "str", description="Summarized text"),
        OutputField("word_count", "int", description="Word count of summary"),
    ],
)
```

## Using Signatures with Agents

```python
from kailash_kaizen import BaseAgent, Signature, InputField, OutputField

class SummaryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="summarizer",
            signature=Signature(
                name="Summarize",
                inputs=[
                    InputField("text", "str", description="Text to summarize"),
                ],
                outputs=[
                    OutputField("summary", "str", description="Summary"),
                ],
            ),
        )

    def run(self, input_text):
        # Agent logic
        words = input_text.split()
        summary = " ".join(words[:20]) + "..."
        return {"response": summary, "summary": summary}

agent = SummaryAgent()
result = agent.run("A long text that needs to be summarized...")
```

## Validation

Signatures validate inputs and outputs automatically:

```python
sig = Signature(
    name="Calculator",
    inputs=[
        InputField("expression", "str", description="Math expression", required=True),
        InputField("precision", "int", description="Decimal places", default=2),
    ],
    outputs=[
        OutputField("result", "float", description="Calculation result"),
    ],
)

# Validate inputs
sig.validate_inputs({"expression": "2+2"})           # OK
sig.validate_inputs({})                                # Raises: expression is required
sig.validate_inputs({"expression": "2+2", "precision": 4})  # OK with override
```

## Chaining Signatures

```python
from kailash_kaizen import Signature, InputField, OutputField
from kailash_kaizen.pipelines import SequentialPipeline

# First agent: extract keywords
extract_sig = Signature(
    name="Extract",
    inputs=[InputField("text", "str")],
    outputs=[OutputField("keywords", "list")],
)

# Second agent: generate report from keywords
report_sig = Signature(
    name="Report",
    inputs=[InputField("keywords", "list")],
    outputs=[OutputField("report", "str")],
)

# Chain agents -- output of first feeds into second
pipeline = SequentialPipeline([extract_agent, report_agent])
result = pipeline.run("Analyze this document about AI safety...")
```

## Common Signature Patterns

### Question Answering

```python
qa_sig = Signature(
    name="QA",
    inputs=[
        InputField("question", "str", description="User question"),
        InputField("context", "str", description="Reference context", default=""),
    ],
    outputs=[
        OutputField("answer", "str", description="Generated answer"),
        OutputField("confidence", "float", description="Confidence score"),
    ],
)
```

### Classification

```python
classify_sig = Signature(
    name="Classify",
    inputs=[
        InputField("text", "str", description="Text to classify"),
        InputField("categories", "list", description="Possible categories"),
    ],
    outputs=[
        OutputField("category", "str", description="Selected category"),
        OutputField("score", "float", description="Classification confidence"),
    ],
)
```

### Data Extraction

```python
extract_sig = Signature(
    name="Extract",
    inputs=[
        InputField("document", "str", description="Source document"),
        InputField("fields", "list", description="Fields to extract"),
    ],
    outputs=[
        OutputField("extracted", "dict", description="Extracted field values"),
        OutputField("missing", "list", description="Fields not found"),
    ],
)
```

## Best Practices

1. **Always provide descriptions** -- they help both developers and LLMs understand the contract
2. **Use defaults for optional fields** -- reduce required configuration
3. **Validate early** -- call `validate_inputs()` before processing
4. **Match output names to downstream inputs** -- enables seamless pipeline chaining
5. **Keep signatures focused** -- each signature should represent one operation

<!-- Trigger Keywords: signature, InputField, OutputField, type-safe, structured output, agent contract, validation -->
