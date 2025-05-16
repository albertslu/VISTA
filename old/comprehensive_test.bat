@echo off
echo Creating comprehensive test tasks for VISTA3D service...

:: Create output directories
mkdir "C:\Users\Albert\output\batch_tests" 2>nul

:: Test 1: Full segmentation on different CT scans
python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\batch_tests\s0031_full" --type "full" --description "Full segmentation of s0031"

python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0052\ct.nii.gz" --output "C:\Users\Albert\output\batch_tests\s0052_full" --type "full" --description "Full segmentation of s0052"

:: Test 2: Point-based liver segmentation on different CT scans
:: We know these coordinates (175,136,141) work well for liver in s0031 from our previous tests
python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\batch_tests\s0031_liver" --type "point" --point "175,136,141" --label 1 --description "Liver segmentation of s0031"

python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0052\ct.nii.gz" --output "C:\Users\Albert\output\batch_tests\s0052_liver" --type "point" --point "175,136,141" --label 1 --description "Liver segmentation of s0052"

:: Test 3: Different organs on the same CT scan
python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\batch_tests\s0031_spleen" --type "point" --point "120,140,140" --label 3 --description "Spleen segmentation of s0031"

python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\batch_tests\s0031_kidney" --type "point" --point "200,140,120" --label 5 --description "Right kidney segmentation of s0031"

python create_task.py --input "C:\Users\Albert\Totalsegmentator_dataset_v201\s0031\ct.nii.gz" --output "C:\Users\Albert\output\batch_tests\s0031_pancreas" --type "point" --point "150,150,130" --label 4 --description "Pancreas segmentation of s0031"

echo Comprehensive test tasks created successfully!
echo The service will process these tasks automatically.
echo Check the processed folder and output directories for results.
echo.
echo NOTE: Full segmentation tasks may take several minutes each to complete.
