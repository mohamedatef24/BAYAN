
import  torch
import  sys
from  pathlib  import  Path

model_path  =  Path(r"e:\تقليد جرامرلي\BAYAN\models\Spelling\Model\Spelling RAW.pt")

try:
    print(f"Loading {model_path}...")
    # Load on CPU to be safe and fast
    state_dict  =  torch.load(model_path, map_location="cpu")
    
    if  isinstance(state_dict, dict):
        print("Loaded as dict. Keys:")
        keys  =  list(state_dict.keys())
        print(f"Total keys: {len(keys)}")
        print("First 20 keys:")
        for  k  in  keys[:20]:
            print(k)
            
        # Check for specific architectures
        if  any(k.startswith("bert.") for  k  in  keys):
            print("\nLooks like BERT.")
        elif  any(k.startswith("roberta.") for  k  in  keys):
            print("\nLooks like RoBERTa.")
        elif  any(k.startswith("transformer.") for  k  in  keys):
            print("\nLooks like a Transformer.")
    else:
        print(f"Loaded object type: {type(state_dict)}")
        print(state_dict)

except  Exception  as  e:
    print(f"Error: {e}")
