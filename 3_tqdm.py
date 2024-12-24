from tqdm import tqdm
import time

# Define the total number of iterations for the progress bar
total_iterations = 100

# Create a tqdm progress bar
progress_bar = tqdm(total=total_iterations, desc="Processing")

# Simulate some task that iterates
for i in range(total_iterations):
    # Do some processing here
    time.sleep(0.1)  # Simulating a delay
    
    # Update the progress bar
    progress_bar.update(1)

# Close the progress bar
progress_bar.close()

print("Task completed!")