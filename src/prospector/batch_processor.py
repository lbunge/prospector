"""Batch processing and progress tracking for large prospecting jobs."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Handle batch processing with checkpointing for large datasets."""

    def __init__(self, checkpoint_dir: str = ".prospector_checkpoints"):
        """
        Initialize batch processor.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def process_in_batches(
        self,
        items: List[Dict],
        process_func: Callable,
        batch_size: int = 10,
        job_name: str = None,
        resume: bool = True
    ) -> List[Dict]:
        """
        Process items in batches with automatic checkpointing.

        Args:
            items: List of items to process
            process_func: Function to process each item (takes item, returns enriched item)
            batch_size: Number of items to process before checkpointing
            job_name: Unique name for this job (for checkpoint file)
            resume: Whether to resume from checkpoint if it exists

        Returns:
            List of processed items
        """
        # Generate job name if not provided
        if not job_name:
            job_name = f"job_{int(time.time())}"

        checkpoint_file = self.checkpoint_dir / f"{job_name}.json"

        # Try to resume from checkpoint
        processed_items = []
        start_index = 0

        if resume and checkpoint_file.exists():
            try:
                checkpoint_data = self._load_checkpoint(checkpoint_file)
                processed_items = checkpoint_data.get('processed_items', [])
                start_index = checkpoint_data.get('last_index', 0)
                logger.info(f"Resuming from checkpoint: {start_index}/{len(items)} items processed")
                print(f"\n✅ Resuming from checkpoint: {start_index}/{len(items)} items already processed")
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}. Starting fresh.")

        # Process items in batches
        total_items = len(items)

        for i in range(start_index, total_items):
            item = items[i]

            try:
                # Process the item
                processed_item = process_func(item)
                processed_items.append(processed_item)

                # Progress update
                if (i + 1) % 5 == 0 or i == total_items - 1:
                    progress = ((i + 1) / total_items) * 100
                    print(f"Progress: {i + 1}/{total_items} ({progress:.1f}%)")

                # Checkpoint after each batch
                if (i + 1) % batch_size == 0 or i == total_items - 1:
                    self._save_checkpoint(
                        checkpoint_file,
                        {
                            'job_name': job_name,
                            'total_items': total_items,
                            'last_index': i + 1,
                            'processed_items': processed_items,
                            'timestamp': datetime.now().isoformat(),
                            'batch_size': batch_size
                        }
                    )
                    logger.info(f"Checkpoint saved at {i + 1}/{total_items}")

            except Exception as e:
                logger.error(f"Error processing item {i}: {e}")
                # Save checkpoint on error so we can resume
                self._save_checkpoint(
                    checkpoint_file,
                    {
                        'job_name': job_name,
                        'total_items': total_items,
                        'last_index': i,  # Don't increment, will retry this item on resume
                        'processed_items': processed_items,
                        'timestamp': datetime.now().isoformat(),
                        'last_error': str(e),
                        'failed_item_index': i
                    }
                )
                print(f"\n⚠️  Error at item {i + 1}: {e}")
                print(f"Progress saved. You can resume with --resume flag.")
                raise

        # Clean up checkpoint file after successful completion
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info("Job completed successfully. Checkpoint file removed.")

        return processed_items

    def _save_checkpoint(self, checkpoint_file: Path, data: Dict):
        """Save checkpoint data to file."""
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _load_checkpoint(self, checkpoint_file: Path) -> Dict:
        """Load checkpoint data from file."""
        with open(checkpoint_file, 'r') as f:
            return json.load(f)

    def list_checkpoints(self) -> List[Dict]:
        """List all available checkpoints."""
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                data = self._load_checkpoint(checkpoint_file)
                checkpoints.append({
                    'job_name': data.get('job_name'),
                    'file': checkpoint_file.name,
                    'progress': f"{data.get('last_index', 0)}/{data.get('total_items', 0)}",
                    'timestamp': data.get('timestamp'),
                    'last_error': data.get('last_error')
                })
            except Exception as e:
                logger.warning(f"Could not read checkpoint {checkpoint_file}: {e}")

        return checkpoints

    def delete_checkpoint(self, job_name: str) -> bool:
        """Delete a specific checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{job_name}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True
        return False

    def clear_all_checkpoints(self):
        """Delete all checkpoint files."""
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            checkpoint_file.unlink()
        logger.info("All checkpoints cleared")


class RateLimiter:
    """Rate limiter with exponential backoff."""

    def __init__(self, calls_per_second: float = 1.0, max_retries: int = 5):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum number of calls per second
            max_retries: Maximum number of retry attempts
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        self.max_retries = max_retries

    def wait(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)

        self.last_call_time = time.time()

    def retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs
    ):
        """
        Execute function with exponential backoff retry.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function call

        Raises:
            Exception if all retries failed
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                self.wait()
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                # Don't retry on certain errors
                if "unauthorized" in str(e).lower() or "forbidden" in str(e).lower():
                    raise

                if attempt < self.max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    backoff_time = 2 ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")

        raise last_exception


class MemoryEfficientProcessor:
    """Process large datasets without loading everything into memory."""

    @staticmethod
    def stream_process(
        items: List[Dict],
        process_func: Callable,
        output_file: str,
        batch_size: int = 100
    ):
        """
        Process items and stream results to file without keeping all in memory.

        Args:
            items: List of items to process
            process_func: Function to process each item
            output_file: File to write results to
            batch_size: Number of items to accumulate before writing
        """
        output_path = Path(output_file)
        temp_file = output_path.with_suffix('.tmp')

        # Write results in batches to avoid memory buildup
        batch = []
        total_processed = 0

        try:
            with open(temp_file, 'w') as f:
                # Start JSON array
                f.write('[\n')

                for i, item in enumerate(items):
                    try:
                        processed_item = process_func(item)
                        batch.append(processed_item)

                        # Write batch to file
                        if len(batch) >= batch_size or i == len(items) - 1:
                            for j, result in enumerate(batch):
                                json.dump(result, f, indent=2)

                                # Add comma if not last item
                                if not (i == len(items) - 1 and j == len(batch) - 1):
                                    f.write(',\n')
                                else:
                                    f.write('\n')

                            # Clear batch from memory
                            total_processed += len(batch)
                            batch = []

                            # Progress update
                            progress = (total_processed / len(items)) * 100
                            print(f"Processed: {total_processed}/{len(items)} ({progress:.1f}%)")

                    except Exception as e:
                        logger.error(f"Error processing item {i}: {e}")
                        continue

                # Close JSON array
                f.write(']\n')

            # Move temp file to final location
            temp_file.rename(output_path)
            logger.info(f"Streaming complete. Results saved to {output_file}")

        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise
