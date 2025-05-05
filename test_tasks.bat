@echo off
echo Creating test tasks for VISTA3D service...

:: Create test task for liver segmentation (we know this works from previous tests)
python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\test_liver" --type "point" --point "175,136,141" --label 1 --description "Liver point-based segmentation"

:: Create test task for spleen segmentation
python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\test_spleen" --type "point" --point "120,140,140" --label 3 --description "Spleen point-based segmentation"

:: Create test task for right kidney segmentation
python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\test_kidney" --type "point" --point "200,140,120" --label 5 --description "Right kidney point-based segmentation"

echo Test tasks created successfully!
echo The service will process these tasks automatically.
echo Check the processed folder and output directories for results.
