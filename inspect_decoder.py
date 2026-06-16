
import  torch
from  pathlib  import  Path

model_path  =  Path(r"e:\تقليد جرامرلي\BAYAN\models\Spelling\Model\Spelling RAW.pt")

try:
    print(f"Loading {model_path}...")
    checkpoint  =  torch.load(model_path, map_location="cpu")
    state_dict  =  checkpoint["model_state_dict"]
    
    print("Checking decoder keys...")
    found_bert  =  False
    for  k  in  state_dict.keys():
        if  k.startswith("decoder.bert"):
            print(f"Found: {k}")
            found_bert  =  True
            break
            
    if  not  found_bert:
        print("No decoder.bert keys found.")
        # Check what IS in decoder
        for  k  in  state_dict.keys():
            if  k.startswith("decoder.") and  not  "cls"  in  k:
                print(f"Decoder key: {k}")
                break

except  Exception  as  e:
    print(f"Error: {e}")
