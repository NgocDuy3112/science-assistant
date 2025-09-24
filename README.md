# Science Assistant using MCP Server and LangGraph


This repository contains a Science Assistant application that leverages the MCP (Multi-Component Processing) server and LangGraph for advanced scientific data processing and analysis. The application is designed to assist researchers and scientists in managing, analyzing, and visualizing scientific data efficiently.

## How to run the application

1. **Clone the Repository**: Start by cloning this repository to your local machine using the following command:
   ```bash
   git clone https://github.com/your-username/science-assistant.git
    cd science-assistant
    ```
2. **Install Dependencies**: Ensure you have Python and uv installed. You can install the required Python packages using pip:
   ```bash
   uv add -r requirements.txt
   ```

3. **Run MCP Server**:
```python
    python -m mcp_servers.arxiv.server
``` 

4. **Run the Application**: Start the Science Assistant application using the following command:
   ```bash
   python -m workflow.run
   ```