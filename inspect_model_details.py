
import  torch
import  sys
from  pathlib  import  Path

model_path  =  Path(r"e:\تقليد جرامرلي\BAYAN\models\Spelling\Model\Spelling RAW.pt")

try:
    print(f"Loading {model_path}...")
    checkpoint  =  torch.load(model_path, map_location="cpu")
    state_dict  =  checkpoint["model_state_dict"]
    
    # 1. Vocab and Hidden Size
    if  "encoder.embeddings.word_embeddings.weight"  in  state_dict:
        shape  =  state_dict["encoder.embeddings.word_embeddings.weight"].shape
        print(f"Vocab Size: {shape[0]}")
        print(f"Hidden Size: {shape[1]}")
    else:
        print("Embeddings weight not found at 'encoder.embeddings.word_embeddings.weight'")
        
        # Try finding any embedding weight
        for  k  in  state_dict.keys():
            if  "embeddings.word_embeddings.weight"  in  k:
                print(f"Found embedding: {k} -> {state_dict[k].shape}")
                
    # 2. Number of layers
    layers  =  set()
    for  k  in  state_dict.keys():
        if  "encoder.encoder.layer."  in  k:
            # Extract layer number
            parts  =  k.split(".")
            try:
                # Find the part after 'layer'
                idx  =  parts.index("layer")
                layer_num  =  int(parts[idx+1])
                layers.add(layer_num)
            except:
                pass
                
    if  layers:
        print(f"Number of layers: {max(layers) + 1}")
    else:
        print("No layers found matching 'encoder.encoder.layer.X'")
        
    # 3. Check for Heads
    print("\nPotential Head Keys:")
    head_keywords  =  ["cls", "linear", "out", "start", "end", "classifier", "generator"]
    for  k  in  state_dict.keys():
        if  any(kw  in  k  for  kw  in  head_keywords) and not "attention" in k and not "intermediate" in k and not  k.startswith("encoder.encoder."):
            print(f"{k} -> {state_dict[k].shape}")

except  Exception  as  e:
    print(f"Error: {e}")
