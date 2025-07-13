import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
import os
import shutil

def accessdb(input):
    args = {}
    args["name"] = "amazon.titan-embed-text-v2:0"
    args["region"] = "eu-central-1"

    script_path = os.path.dirname(os.path.abspath(__file__))

    model = get_registry().get("bedrock-text").create(**args)
    table_name = "test"

    chunks = []
    source_dir = f"{script_path}/source_documents"
    for file in os.listdir(source_dir):
        with open(os.path.join(source_dir, file), "r", encoding='utf-8') as f:
            text = f.read()
            chunks.append({"text": text})

    class TextModel(LanceModel):
        text: str = model.SourceField()
        vector: Vector(model.ndims()) = model.VectorField() # type: ignore

    db = lancedb.connect(f"{script_path}/tables")
    db_tables= db.table_names()
    if table_name not in db_tables:
        print(f"Creating table {table_name}...")
        tbl = db.create_table(table_name, schema=TextModel, mode="overwrite")
        tbl.add(chunks)
    else:
        print(f"Table {table_name} already exists, using existing table...")
        tbl = db.open_table(table_name)

    #input = "EcoClean"
    rs = tbl.search(input).limit(5) #5 è il limite sui chunk, in questo caso ogni file di testo è un chunk
    #print(rs.to_pydantic(TextModel))  
    #print(rs.to_pandas()) #questo devo mandarlo in input all'llm
    results = rs.to_pandas()
    results = results.drop(columns=['vector', '_distance'])
    prompt = results.iloc[0]['text'] #questo è quello da passare all'llm quindi basta che ritorno questo
    #print(prompt)
    return prompt

def updatedb():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.dirname(os.path.abspath(__file__))
    #print("Cartella:", os.path.dirname(os.path.abspath(__file__)))


    #folder_path = os.path.join(BASE_DIR, 'utils\tables\test.lance')
    #print("Cartella corrente:", os.getcwd())
    #path = r"\tables\test.lance\data"
    folder_path = os.path.join(file_path, '\tables\\test.lance\data')
    #print("Cartella corrente:", folder_path)
    from pathlib import Path

    # Ottieni il path della cartella corrente
    base = Path(__file__).parent

    # Costruisci il percorso relativo
    data_path = base / 'tables'

    #print("Percorso assoluto:", data_path.resolve())

    if os.path.exists(data_path.resolve()):
        shutil.rmtree(data_path.resolve())
        #print("Folder and all contents deleted.")
    else:
        print("Folder not found.")
    return "0"

#accessdb("input")