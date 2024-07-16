import os
import pandas as pd
import ray

producer_task_name = "task::ReadRange->MapBatches(produce)"
consumer_task_name = "task::MapBatches(consume)"
inference_task_name = "task::MapBatches(inference)"

COLORS = {
    producer_task_name: "rail_response",
    consumer_task_name: "cq_build_passed",
    inference_task_name: "cq_build_failed"
}

def assign_slots(events, num_cpus, num_gpus):
    # Initialize slot allocation
    slots = [None] * (num_cpus + num_gpus)
    slots_to_cat = [None] * (num_cpus + num_gpus)
    events = sorted(events, key=lambda x: x["ts"])
    
    for event in events:
        start_time = event["ts"]
        end_time = start_time + event["dur"]
        assigned = False
        # Find an available slot for the worker
        for i in range(num_cpus + num_gpus):
            if event['cat'] in [producer_task_name, consumer_task_name] and i > num_cpus:
                continue
            if event['cat'] in [inference_task_name] and i < num_cpus: 
                continue
            if slots[i] is None or slots[i] <= start_time:
                if slots_to_cat[i] == event['cat']:
                    slots[i] = end_time
                    event["tid"] = f"slot:{i}"
                    assigned = True
                    break
        if not assigned:
            for i in range(num_cpus + num_gpus):
                if event['cat'] in [producer_task_name, consumer_task_name] and i > num_cpus:
                    continue
                if event['cat'] in [inference_task_name] and i < num_cpus: 
                    continue
                if slots[i] is None or slots[i] <= start_time:
                    slots[i] = end_time
                    event["tid"] = f"slot:{i}"
                    slots_to_cat[i] = event['cat']
                    assigned = True
                    break        
            else:
                raise ValueError("Not enough slots available for all tasks.")
    
    return events

def save_timeline(addr: str):
    ray.timeline(addr)
    df = pd.read_json(addr)
    filtered_df = df[df["cat"].isin(COLORS.keys())]
    filtered_df.loc[:, "cname"] = filtered_df["cat"].apply(lambda x: COLORS[x])
    filtered_df.to_json(addr, orient="records")
    print(f"Processed and saved modified data to {addr}")

def save_timeline_with_cpus_gpus(addr: str, num_cpus: int, num_gpus: int):
    ray.timeline(addr)
    df = pd.read_json(addr)
    filtered_df = df[df["cat"].isin(COLORS.keys())]
    filtered_df.loc[:, "cname"] = filtered_df["cat"].apply(lambda x: COLORS[x])
    
    # Assign slots to events
    events = filtered_df.to_dict(orient="records")
    updated_events = assign_slots(events, num_cpus, num_gpus)
    
    # Save the updated events back to the JSON file
    updated_df = pd.DataFrame(updated_events)
    updated_df.to_json(addr, orient="records")
    print(f"Processed and saved modified data to {addr}")
    
def read_and_save_timeline_with_cpus_gpus(addr: str, num_cpus: int, num_gpus: int):
    
    df = pd.read_json(addr)
    filtered_df = df[df["cat"].isin(COLORS.keys())]
    filtered_df.loc[:, "cname"] = filtered_df["cat"].apply(lambda x: COLORS[x])
    
    # Assign slots to events
    events = filtered_df.to_dict(orient="records")
    updated_events = assign_slots(events, num_cpus, num_gpus)
    
    # Save the updated events back to the JSON file
    updated_df = pd.DataFrame(updated_events)
    updated_df.to_json(addr, orient="records")
    print(f"Processed and saved modified data to {addr}")
    
# if __name__ == "__main__":
#     read_and_save_timeline_with_cpus_gpus('timeline_flink_three_stage.json', 8, 4)
