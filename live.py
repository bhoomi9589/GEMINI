import streamlit as st
import asyncio
import threading
import queue
import logging
import time
from typing import Optional, Any
import io

# Suppress Streamlit warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)

# Configure Streamlit page
st.set_page_config(
    page_title="Media Processor",
    page_icon="🎬",
    layout="wide"
)

class MediaProcessor:
    def __init__(self):
        self.processing_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = False
    
    def start_background_processor(self):
        """Start background processor thread"""
        if not self.is_running:
            self.is_running = True
            processor_thread = threading.Thread(
                target=self._background_worker, 
                daemon=True
            )
            processor_thread.start()
    
    def _background_worker(self):
        """Background worker that processes media without Streamlit calls"""
        while self.is_running:
            try:
                if not self.processing_queue.empty():
                    task = self.processing_queue.get(timeout=1)
                    result = self._process_media_item(task)
                    self.result_queue.put(result)
                else:
                    time.sleep(0.1)
            except queue.Empty:
                continue
            except Exception as e:
                self.result_queue.put({"error": str(e)})
    
    def _process_media_item(self, task_data):
        """Process media item without any Streamlit calls"""
        try:
            file_data = task_data.get('file_data')
            process_type = task_data.get('type', 'unknown')
            
            # Simulate processing time
            time.sleep(2)
            
            # Your actual media processing logic here
            result = {
                "status": "success",
                "type": process_type,
                "size": len(file_data) if file_data else 0,
                "processed_at": time.time(),
                "message": f"Successfully processed {process_type} file"
            }
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "processed_at": time.time()
            }
    
    def add_task(self, file_data, file_type):
        """Add processing task to queue"""
        task = {
            "file_data": file_data,
            "type": file_type,
            "timestamp": time.time()
        }
        self.processing_queue.put(task)
    
    def get_results(self):
        """Get all available results"""
        results = []
        while not self.result_queue.empty():
            try:
                result = self.result_queue.get_nowait()
                results.append(result)
            except queue.Empty:
                break
        return results

# Initialize session state
def initialize_session_state():
    if 'media_processor' not in st.session_state:
        st.session_state.media_processor = MediaProcessor()
    
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = []
    
    if 'processor_started' not in st.session_state:
        st.session_state.media_processor.start_background_processor()
        st.session_state.processor_started = True

# Async processing function (runs in main thread)
async def async_process_multiple_files(files):
    """Async processing that doesn't interfere with Streamlit context"""
    results = []
    
    for file in files:
        # Process each file asynchronously
        await asyncio.sleep(0.1)  # Simulate async work
        
        # Add to background processor queue
        st.session_state.media_processor.add_task(
            file_data=file.read() if file else None,
            file_type=file.type if hasattr(file, 'type') else 'unknown'
        )
        
        results.append({
            "filename": file.name if hasattr(file, 'name') else 'unknown',
            "status": "queued"
        })
    
    return results

def main():
    # Initialize everything
    initialize_session_state()
    
    st.title("🎬 Media Processor")
    st.markdown("Upload and process media files without context warnings")
    
    # Sidebar for controls
    with st.sidebar:
        st.header("Controls")
        
        # Queue status
        queue_size = st.session_state.media_processor.processing_queue.qsize()
        st.metric("Queue Size", queue_size)
        
        # Clear results
        if st.button("Clear Results"):
            st.session_state.processing_results = []
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Upload Files")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose media files",
            accept_multiple_files=True,
            type=['mp4', 'avi', 'mov', 'mp3', 'wav', 'jpg', 'png']
        )
        
        # Process button
        if st.button("Process Files", disabled=not uploaded_files):
            if uploaded_files:
                with st.spinner("Adding files to processing queue..."):
                    # Use asyncio in main thread - this is safe
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        queued_results = loop.run_until_complete(
                            async_process_multiple_files(uploaded_files)
                        )
                        st.success(f"Added {len(queued_results)} files to processing queue!")
                        
                        # Display queued files
                        for result in queued_results:
                            st.info(f"Queued: {result['filename']}")
                            
                    finally:
                        loop.close()
    
    with col2:
        st.header("Processing Results")
        
        # Check for new results
        new_results = st.session_state.media_processor.get_results()
        if new_results:
            st.session_state.processing_results.extend(new_results)
            st.rerun()
        
        # Display results
        if st.session_state.processing_results:
            for i, result in enumerate(reversed(st.session_state.processing_results[-10:])):
                with st.expander(f"Result {len(st.session_state.processing_results) - i}"):
                    if result.get('status') == 'success':
                        st.success(result.get('message', 'Processing completed'))
                        st.json({
                            'type': result.get('type'),
                            'size': result.get('size'),
                            'processed_at': time.ctime(result.get('processed_at', 0))
                        })
                    else:
                        st.error(f"Error: {result.get('error', 'Unknown error')}")
        else:
            st.info("No results yet. Upload and process files to see results here.")
        
        # Auto-refresh button
        if st.button("🔄 Refresh Results"):
            st.rerun()
    
    # Auto-refresh every 2 seconds if there are items in queue
    if queue_size > 0:
        time.sleep(2)
        st.rerun()

if __name__ == "__main__":
    main()