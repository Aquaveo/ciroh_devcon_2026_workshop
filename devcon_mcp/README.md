## MCP Servers

## Why

It is a protocol that allows the llms to talk to tools. 

## Prompt templates

## why

Allows to recycle prompts and give better isntructions to the llms 

## Pyndatic Validation

### why

A better validation means that the llm can look a better schema, and resolve what to sue with arguments correctly.



## Answers

### 1A

Replace the following `items=[]` with

```python
    this is the answer for the answer 
    files = sorted(files)
    items = [{"name": f.split("/")[-1], "path": f} for f in files]
```
### 1B.

Replace the `return` with the following:

```python
    the following is the answer fir the prompt template
        return (
            f"List the available output files for the {configuration} configuration on {date}, "
            f"{forecast} forecast, cycle {cycle}, vpu {vpu}."
    )
```