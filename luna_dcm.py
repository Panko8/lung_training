"""
This file is made to seperate class defintion and instanciation.
Otherwise, it will throw an error.
"""
import SimpleITK as sitk
import numpy as np

def load_itk(filename):
    '''
    This funciton reads a '.mhd' file using SimpleITK and return the image array, origin and spacing of the image.
    '''
    # Reads the image using SimpleITK
    itkimage = sitk.ReadImage(filename)
    # Convert the image to a  numpy array first and then shuffle the dimensions to get axis in the order z,y,x
    ct_scan = sitk.GetArrayFromImage(itkimage)
    # Read the origin of the ct_scan, will be used to convert the coordinates from world to voxel and vice versa.
    origin = np.array(list(reversed(itkimage.GetOrigin())))
    # Read the spacing along each dimension
    spacing = np.array(list(reversed(itkimage.GetSpacing())))
    return ct_scan, origin, spacing

class FakeDicomReaderForLuna():
    def __init__(self, path, pid, spacing, raw_slices):
        self.path = path
        self.data_path = path
        self.pid = pid
        self.uid = pid
        self.PixelSpacing = spacing[2], spacing[1]
        self.SliceThickness = spacing[0]
        self.raw_slices = raw_slices

    @property
    def transform(self):
        return (self.SliceThickness, self.PixelSpacing[1], self.PixelSpacing[0]) #z,y,x
        
    def __len__(self):
        return len(self.raw_slices)
    
    def check(self):
        return self.raw_slices
    
    def get_series_with_transform(self, norm_hu=True):
        assert norm_hu, "Luna image had already be converted to grayscale"
        scan, _, _ = load_itk(self.path)
        transform = [self.SliceThickness, self.PixelSpacing[1], self.PixelSpacing[0]]
        return scan, transform
    
    def get_series(self, norm_hu=True):
        scan, _ = self.get_series_with_transform(norm_hu)
        return scan

