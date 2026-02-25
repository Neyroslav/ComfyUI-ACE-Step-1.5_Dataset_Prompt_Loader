# ACE Dataset Prompt Loader (ComfyUI Node)

**ACE Dataset Prompt Loader** is a custom ComfyUI node designed to extract structured prompt data from ACE Step 1.5 dataset JSON files.

It allows you to reuse the exact musical and textual attributes used during LoRA training, helping generate outputs that better match the learned style and tonal characteristics.

---

## ✨ Why This Node Exists

LoRA models trained on ACE Step 1.5 datasets learn relationships between:

- caption / description
    
- musical key & scale
    
- BPM
    
- time signature
    
- language
    
- lyrics
    
- duration
    
- custom tags
    

When generating music or prompts using the same attributes the LoRA was trained on, results become:

✅ more stylistically consistent  
✅ more tonally accurate  
✅ closer to training distribution  
✅ less “random” and more authentic

This node extracts those values directly from the dataset so you can reuse them in generation workflows.

---

## 🧠 What It Does

The node loads an ACE dataset `.json` and outputs structured fields from samples:

- Caption
    
- Lyrics / formatted lyrics
    
- BPM
    
- Key & Scale
    
- Time Signature
    
- Duration
    
- Language
    
- Filename
    
- Custom tag
    

These outputs can be connected directly to prompt builders, conditioning nodes, or generation workflows.

---

## 📥 Input Parameters

### Required

**dataset_json_path**  
Path to ACE dataset JSON file.

**mode**  
Select how values are retrieved:

- **random_fields** – random value for each field independently
    
- **random_track** – random sample (all fields from one track)
    
- **sequential_cycle** – cycles through tracks sequentially
    
- **specific_track** – load a specific track
    

---

### Optional

**seed**  
Controls randomness for reproducible results.

**track_number**  
Used when `specific_track` mode is selected.