
import uvicorn
from multiomics_api_server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
