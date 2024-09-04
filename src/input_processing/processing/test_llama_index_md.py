from llama_index.core.node_parser import MarkdownNodeParser
from chunking import InputProcessor
from llama_index.core import Document


parser = MarkdownNodeParser()
input_processor = InputProcessor('supabase.com_docs__20240826_212435.json')
input_data = input_processor.load_json()

# Create a Document object from the first markdown entry (for demonstration)
doc = Document(text=input_data['data'][0]['markdown'])

# Parse the document into nodes
nodes = parser.get_nodes_from_documents([doc])

# Print the nodes
for i, node in enumerate(nodes):
    print(f"Node {i + 1}:")
    print(f"Text: {node.text[:100]}...")  # Print first 100 characters
    print(f"Metadata: {node.metadata}")
    print("---")
