import os 
from typing import Optional, Dict, Any

#--- watsonx.ai (Granite) ---

try:
     from ibm_watsonx_ai import Credentials 
     from ibm_watsonx_ai.foundation_models import Model 
except Exception:  # package might not be installed yet 
    Credentials = None 
    Model = None

#--- IBM Watson NLU (classic) ---

try: 
    from ibm_watson import NaturalLanguageUnderstandingV1 
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator 
    from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions 
except Exception: 
    NaturalLanguageUnderstandingV1 = None 
    IAMAuthenticator = None
    Features = None 
    EntitiesOptions = None
    KeywordsOptions = None

class IBMProviders: 
    def __init__(self):
         # watsonx.ai 
         self.wx_apikey = os.getenv("WATSONX_APIKEY") 
         self.wx_url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com") 
         self.wx_project = os.getenv("WATSONX_PROJECT_ID") 
         self.model_id = os.getenv("GRANITE_MODEL_ID", "ibm/granite-13b-chat-v2") 
         self.generation_parameters = { 
             "decoding_method": "greedy", 
             "max_new_tokens": 256, 
             "min_new_tokens": 1, 
             "temperature": 0.2, 
             "top_k": 50, 
             "top_p": 1.0 
         } 
         self._wx_model = None

         # NLU
         self.nlu_apikey = os.getenv("WATSON_NLU_APIKEY")
         self.nlu_url = os.getenv("WATSON_NLU_URL")
         self._nlu_client = None

    def wx_ready(self) -> bool:
      return bool(self.wx_apikey and self.wx_project and Model is not None)

    def nlu_ready(self) -> bool:
      return bool(self.nlu_apikey and self.nlu_url and NaturalLanguageUnderstandingV1 is not None)
    def wx_model(self):
     if not self.wx_ready():
        return None
     if self._wx_model is None:
        creds = Credentials(self.wx_apikey, self.wx_url)
        self._wx_model = Model(
            model_id=self.model_id,
            credentials=creds,
            project_id=self.wx_project,
            params=self.generation_parameters,
        )
     return self._wx_model

    def nlu_client(self):
     if not self.nlu_ready():
        return None
     if self._nlu_client is None:
        auth = IAMAuthenticator(self.nlu_apikey)
        self._nlu_client = NaturalLanguageUnderstandingV1(version="2021-08-01", authenticator=auth)
        self._nlu_client.set_service_url(self.nlu_url)
     return self._nlu_client

# ----- High-level helpers -----
    def wx_generate(self, system_prompt: str, user_prompt: str) -> Optional[str]:
     mdl = self.wx_model()
     if mdl is None:
        return None
    # simple chat-style prompt
     prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>"
     try:
        resp = mdl.generate_text(prompt=prompt)
        if isinstance(resp, dict):
            return resp.get("results", [{}])[0].get("generated_text", "")
        # fallback for SDKs that return list
        if isinstance(resp, list) and resp:
            return resp[0].get("generated_text", "")
     except Exception:
      return None
     return None

    def nlu_entities(self, text: str) -> Dict[str, Any]:
     cli = self.nlu_client()
     if cli is None:
        return {}
     try:
        features = Features(entities=EntitiesOptions(emotion=False, sentiment=False, limit=50),
                            keywords=KeywordsOptions(limit=25))
        res = cli.analyze(text=text, features=features, language=None).get_result()
        return res
     except Exception:
        return {}

IBM = IBMProviders()
