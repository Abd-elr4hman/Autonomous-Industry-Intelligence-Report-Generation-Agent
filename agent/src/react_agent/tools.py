"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

import base64
import uuid
from io import BytesIO
from typing import Any, Callable, List, Optional, cast

import boto3
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langchain_experimental.utilities import PythonREPL
from typing_extensions import Annotated

from react_agent.configuration import Configuration


async def search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> Optional[list[dict[str, Any]]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    configuration = Configuration.from_runnable_config(config)
    wrapped = TavilySearchResults(max_results=configuration.max_search_results)
    result = await wrapped.ainvoke({"query": query})
    return cast(list[dict[str, Any]], result)


repl = PythonREPL()


## TODO: sync function blocks the event loop. needs to either run async or be run in a threadpool
@tool
def python_repl_tool(
    code: Annotated[str, "The python code to execute to generate your chart."],
    name: Annotated[str, "Title of the chart"],
    description: Annotated[str, "description of what the chart represent"],
):
    """Use this to execute python code to make charts and plots.

    You always need to return the output plot or chart in `print(...)`.
    # Don't show the plots you create only return them. 
    # Return the plot or chart by running the following code after creating the plot:
    ```
    import io
    import base64
    import matplotlib.pyplot as plt
    # always add this line of code to avoid issues
    matplotlib.use('Agg')

    # add any imports you need here

    # 1. write code to generate plot here

    # 2. Save to BytesIO buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()

    # 3. Encode PNG bytes as Base64 (text-safe)
    png_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    # 4. Print to stdout (can be decoded later)
    print(png_base64)
    ```
    
    """
    try:
        png_base64 = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    
    # Upload to S3
    decoded_bytes = base64.b64decode(png_base64) 

    image_uuid = str(uuid.uuid4())
    filename = f'{image_uuid}{name}.png'.replace(" ", "_")

    s3 = boto3.client('s3')
    s3.upload_fileobj(
        BytesIO(decoded_bytes),
        'industry-reports-plots',
        filename,
        ExtraArgs={'ContentType': 'image/png'}
    ) 

    result = {
        "url": f"https://industry-reports-plots.s3.amazonaws.com/{filename}",
        "name": name,
        "description":description
    }
    return result


TOOLS: List[Callable[..., Any]] = [search, python_repl_tool]
