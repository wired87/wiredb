# File Manager & Extraction Pipeline

The File Manager handles the ingestion of raw files (images, PDFs, text) to extract structural components for the coding brain.

## Capabilities

- **Deep Extraction**: Uses Vertex AI (Gemini 2.5 Pro) to analyze file content.
- **Entity Recognition**: Identifies:
    - **Params**: Numerical constants or variables used in equations.
    - **Methods**: Mathematical formulas or logic blocks.
    - **Fields**: Class variables or configuration settings.
- **Graph Integration**: Uses `ModuleCreator` and `QFUtils` to build an in-memory graph of the extracted code structure.
- **Optimization**: Automatically converts extracted Python formulas into JAX-compatible code.

## Testing the Pipeline

You can verify the extraction logic without writing to the database by using the `test_pipeline.py` script.

### Prerequisites
- `image.png` must exist in `core/file_manager/`.
- Vertex AI credentials must be configured.

### Running the Test
Execute the following command from the project root:

```bash
python -m core.file_manager.test_pipeline
```

### What it does
1. Loads `image.png`.
2. Encodes it to base64.
3. Calls `file_manager.process_and_upload_file_config(..., testing=True)`.
4. **Skips** all BigQuery upsert operations.
5. Prints the classification result (Module, Params, Methods, Fields).
