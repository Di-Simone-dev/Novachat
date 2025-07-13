import utils.create_vector # type: ignore #per il rag

from flask import Flask, render_template, request, jsonify
import boto3
import logging
import json
import os
import markdown


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# insert credentials here
os.environ['AWS_ACCESS_KEY_ID'] = ""  
os.environ['AWS_SECRET_ACCESS_KEY'] = ""
os.environ['AWS_SESSION_TOKEN'] = ""
# or in ~/.aws/credentials file with format:
# [default]
# aws_access_key_id = YOUR_ACCESS_KEY
# aws_secret_access_key = YOUR_SECRET   
# aws_session_token = YOUR_SESSION_TOKEN

#upload txt
from werkzeug.utils import secure_filename

# Create a Bedrock client
client = boto3.client('bedrock-runtime', region_name='eu-central-1')  # Change region if needed

# Function to call Converse API
def call_converse_api(system_message, user_message, model_id, streaming=False,guardrails=False):
    """
    Calls the AWS Bedrock Converse API.
    
    Parameters:
    - system_message: The initial system message
    - user_message: The user's input message
    - model_id: The name of the model to use
    - streaming: Boolean indicating if streaming mode is on/off
    
    Returns:
    - The response from the API
    """

    # Inference parameters to use.
    temperature = 0.5
    maxTokens = 1000
    topP = 0.9
    top_k = 20

    # Base inference parameters to use.
    inference_config = {
      "temperature": temperature,
      "maxTokens": maxTokens,
      "topP": topP,
    }
    # Additional inference parameters to use.
    additional_model_fields = {
      "inferenceConfig": {
        "topK": top_k
      }
    }
    
    # Setup the system prompts and messages to send to the model.
    system_prompts = [{"text": system_message}]
    message = {
        "role": "user",
        "content": [{"text": user_message}]
    }
    messages = [message]
    
    if not streaming:

      guardrail_config = {
          "guardrailIdentifier": "bz9vanuflnf5",
          "guardrailVersion": "1",
          "trace": "enabled"
      }  

    # Call the Converse API
      if guardrails:
        response = client.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields,
        guardrailConfig=guardrail_config
      ) #l'ultima riga è per il setting del guardrail
      else:
        response = client.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields
      )

      logger.info(f"Response from Converse API:\n{json.dumps(response, indent=2)}")
      #print('\n\n###########################################\n\n')
      out = response["output"]["message"]["content"][0]["text"]

      # Log token usage.
      token_usage = response['usage']
      #print('\n\n###########################################\n\n')
      logger.info("Input tokens: %s", token_usage['inputTokens'])
      logger.info("Output tokens: %s", token_usage['outputTokens'])
      logger.info("Total tokens: %s", token_usage['totalTokens'])
      logger.info("Stop reason: %s", response['stopReason'])
    else:

      guardrail_config = {
          "guardrailIdentifier": "bz9vanuflnf5",
          "guardrailVersion": "1",
          "trace": "enabled",
          "streamProcessingMode": "sync"
      } 

      response = client.converse_stream(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields
      )
      stream = response.get('stream')
      if stream:
          for event in stream:

              if 'messageStart' in event:
                  print(f"\nRole: {event['messageStart']['role']}")

              if 'contentBlockDelta' in event:
                  print(event['contentBlockDelta']['delta']['text'], end="")

              if 'messageStop' in event:
                  print(f"\nStop reason: {event['messageStop']['stopReason']}")

              if 'metadata' in event:
                  metadata = event['metadata']
                  if 'usage' in metadata:
                      print("\nToken usage")
                      print(f"Input tokens: {metadata['usage']['inputTokens']}")
                      print(
                          f":Output tokens: {metadata['usage']['outputTokens']}")
                      print(f":Total tokens: {metadata['usage']['totalTokens']}")
                  if 'metrics' in event['metadata']:
                      print(
                          f"Latency: {metadata['metrics']['latencyMs']} milliseconds")
    return out                

model_id = "eu.amazon.nova-lite-v1:0"  # Replace with actual model name
streaming = False  # Set to True to enable streaming
system_message = "Sei un assistente conciso"

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    #guardrails può essere attivato o meno a priori
    user_message = request.json.get("message")
    #user_message è l'input 
    rag = request.json.get("rag", False)
    #print("Rag attivo:", rag)
    guardrails = request.json.get("guardrails", False)
    #print("Guardrails attivo:",guardrails)
    if rag:
        rs = utils.create_vector.accessdb(user_message)
        user_message +=" "  
        user_message +=rs #aggiungo il chunk con minor distanza ottenuto dal database
        
    out=call_converse_api(system_message, user_message, model_id, streaming,guardrails)

    raw = repr(out)
    html = markdown.markdown(raw[1:-1])
    return jsonify({"reply": html})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'utils\source_documents')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'txt'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/upload", methods=["POST"])
def upload():
    

    if 'file' not in request.files:
        return jsonify({"error": "Nessun file inviato"}), 400

    f = request.files['file']
    if f.filename == '':
        return jsonify({"error": "Nessun file selezionato"}), 400

    if not allowed_file(f.filename):
        return jsonify({"error": "Solo file .txt sono accettati"}), 400

    filename = secure_filename(f.filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    print(f"Salvataggio in: {filepath}")
    f.save(filepath)

    if os.path.exists(filepath):
        print("✅ File salvato con successo.")
        utils.create_vector.updatedb() # QUI CANCELLO LA CARTELLA DATA
        #Il database viene ricreato appena si prova ad utilizzare il rag, non viene ricreato subito

    else:
        print("❌ ERRORE: Il file NON è stato salvato.")

    # Leggi il contenuto
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()

    return jsonify({"content": content})

if __name__ == "__main__":
    app.run(debug=True)
