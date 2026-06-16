
import  torch
import  sys
from  pathlib  import  Path

model_path  =  Path(r"e:\تقليد جرامرلي\BAYAN\models\Spelling\Model\Spelling RAW.pt")

try:
    print(f"Loading {model_path}...")
    checkpoint  =  torch.load(model_path, map_location="cpu")
    
    if  "model_state_dict"  in  checkpoint:
        state_dict  =  checkpoint["model_state_dict"]
        print("Found model_state_dict. Keys:")
        keys  =  list(state_dict.keys())
        print(f"Total weight keys: {len(keys)}")
        print("First 20 weight keys:")
        for  k  in  keys[:20]:
            print(k)
            
        # Check architecture
        if  any(k.startswith("bert.") for  k  in  keys):
            print("\nArchitecture likely: BERT")
        elif  any(k.startswith("roberta.") for  k  in  keys):
            print("\nArchitecture likely: RoBERTa")
        elif  any(k.startswith("transformer.") for  k  in  keys): # often T5
            print("\nArchitecture likely: Transformer (T5/Bart)")
        elif  any(k.startswith("model.encoder.") for  k  in  keys): # mBART/Bart
            print("\nArchitecture likely: mBART/Bart")
    else:
        print("model_state_dict not found in checkpoint.")

except  Exception  as  e:
    print(f"Error: {e}")
