from typing import Any, Dict

import chainlit as cl


class MockFirecrawlTool:
    def index(self, indexing_info: dict[str, Any]):
        print(f"Indexing with parameters: {indexing_info}")


firecrawl_tool = MockFirecrawlTool()


@cl.on_chat_start
async def on_chat_start():
    welcome_text = """
    Welcome to the OmniClaude docs bot!

    Available commands:
    - @docs add "url" : Add a new URL to index
    - @docs list : List all indexed URLs
    - @docs remove "url" : Remove a URL from the index

    Type a command to get started.
    """
    await cl.Message(content=welcome_text).send()


@cl.on_message
async def handle_message(message: cl.Message):
    if message.content.startswith("@docs add"):
        await handle_docs_add_command(message.content)
    elif message.content.startswith("@docs list"):
        await handle_docs_list_command()
    elif message.content.startswith("@docs remove"):
        await handle_docs_remove_command(message.content)
    else:
        await cl.Message(content="Invalid command. Use @docs add, list, or remove.").send()


async def handle_docs_add_command(command: str):
    parts = command.split('"')
    if len(parts) != 3:
        await cl.Message(content='Invalid command. Use @docs add "url"').send()
        return

    url = parts[1]
    await start_indexing_flow(url)


async def start_indexing_flow(url: str):
    await cl.Message(content=f"Starting indexing process for {url}").send()

    # Exclude patterns
    exclude_guidance = cl.Text(
        content="""Exclude Patterns Guide:
    - Use patterns to exclude specific URLs or directories
    - Separate multiple patterns with commas
    - Examples:
      - /blog/* (excludes all blog posts)
      - /author/*, /tag/* (excludes author and tag pages)""",
        name="Exclude Patterns Guide",
        display="inline",
    )

    await cl.Message(content="Specify patterns to exclude:", elements=[exclude_guidance]).send()
    exclude_patterns_msg = await cl.AskUserMessage(content="Enter exclude patterns (comma-separated):").send()
    exclude_patterns = exclude_patterns_msg["output"] if exclude_patterns_msg else ""

    # Max pages
    max_pages_guidance = cl.Text(
        content="""Max Pages Guide:
    - Set the maximum number of pages to crawl
    - Use a reasonable number to avoid overloading the server
    - Example: 100 (will crawl up to 100 pages)""",
        name="Max Pages Guide",
        display="inline",
    )

    await cl.Message(content="Specify maximum pages to crawl:", elements=[max_pages_guidance]).send()
    max_pages_msg = await cl.AskUserMessage(content="Enter maximum pages number:").send()
    max_pages = max_pages_msg["output"] if max_pages_msg else ""

    # Crawl depth
    crawl_depth_guidance = cl.Text(
        content="""Crawl Depth Guide:
    - Determines how deep the crawler will go into the site structure
    - Higher numbers may result in longer crawl times
    - Examples:
      - 1 (only the homepage)
      - 3 (homepage, linked pages, and pages linked from those)""",
        name="Crawl Depth Guide",
        display="inline",
    )

    await cl.Message(content="Specify crawl depth:", elements=[crawl_depth_guidance]).send()
    crawl_depth_msg = await cl.AskUserMessage(content="Enter crawl depth number:").send()
    crawl_depth = crawl_depth_msg["output"] if crawl_depth_msg else ""

    indexing_info = {
        "url": url,
        "exclude_patterns": exclude_patterns,
        "max_pages": max_pages,
        "crawl_depth": crawl_depth,
    }

    # Display collected information
    info_message = f"""
    Indexing content with the following parameters:
    - URL: {url}
    - Exclude patterns: {exclude_patterns}
    - Max pages: {max_pages}
    - Crawl depth: {crawl_depth}
    """
    await cl.Message(content=info_message).send()

    # Mock indexing process with progress updates
    await cl.Message(content="Starting indexing process...").send()
    await cl.Message(content="Crawling pages...").send()
    await cl.Message(content="Processing content...").send()
    firecrawl_tool.index(indexing_info)
    await cl.Message(content=f"Content from {url} has been indexed successfully.").send()

    await cl.Message(content="Indexing process completed. You can now ask questions about the indexed content.").send()


async def handle_docs_list_command():
    # This would typically fetch from a database. Using a mock list for demonstration.
    indexed_urls = ["https://example.com", "https://another-example.com"]
    list_message = "Currently indexed URLs:\n" + "\n".join(f"- {url}" for url in indexed_urls)
    await cl.Message(content=list_message).send()


async def handle_docs_remove_command(command: str):
    parts = command.split('"')
    if len(parts) != 3:
        await cl.Message(content='Invalid command. Use @docs remove "url"').send()
        return

    url = parts[1]
    # This would typically remove from a database. Using a mock removal for demonstration.
    await cl.Message(content=f"Removing {url} from the index...").send()
    await cl.Message(content=f"{url} has been removed from the index.").send()


if __name__ == "__main__":
    cl.run()
