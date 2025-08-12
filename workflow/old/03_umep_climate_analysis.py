#qgis_path = r"C:\Program Files\QGIS 3.34.12"

import os
import sys

# ----------------------------------------------------------------------------------
# 🔧 Patch os.add_dll_directory to skip invalid paths like '.' or ''
# ----------------------------------------------------------------------------------
original_add_dll_directory = os.add_dll_directory

def safe_add_dll_directory(p):
    if os.path.isabs(p) and os.path.isdir(p):
        return original_add_dll_directory(p)
    # Ignore invalid paths silently
    return None

os.add_dll_directory = safe_add_dll_directory

# ----------------------------------------------------------------------------------
# 📁 Define your QGIS install location
# ----------------------------------------------------------------------------------
QGIS_PATH = r"C:\Program Files\QGIS 3.34.12"

# ----------------------------------------------------------------------------------
# 🧪 Construct safe DLL search paths
# ----------------------------------------------------------------------------------
dll_paths = [
    os.path.join(QGIS_PATH, 'bin'),
    os.path.join(QGIS_PATH, 'apps', 'qgis-ltr', 'bin'),
    os.path.join(QGIS_PATH, 'apps', 'Qt5', 'bin')
]

# Filter current PATH for valid absolute directories only
original_path = os.environ.get('PATH', '')
valid_paths = [p for p in original_path.split(';') if os.path.isabs(p) and os.path.isdir(p)]

# Combine and set PATH
os.environ['PATH'] = ';'.join(dll_paths + valid_paths)

# ----------------------------------------------------------------------------------
# 📚 Add QGIS Python modules to sys.path
# ----------------------------------------------------------------------------------
sys.path.append(os.path.join(QGIS_PATH, 'apps', 'qgis-ltr', 'python'))
sys.path.append(os.path.join(QGIS_PATH, 'apps', 'qgis-ltr', 'python', 'plugins'))
sys.path.append(os.path.join(QGIS_PATH, 'apps', 'Python312', 'Lib', 'site-packages'))

#Add UMEP from user-installed plugin location
sys.path.append(r"C:\Users\Ardo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins")

# ----------------------------------------------------------------------------------
# ⚙️ Set QGIS environment variables
# ----------------------------------------------------------------------------------
os.environ['QGIS_PREFIX_PATH'] = os.path.join(QGIS_PATH, 'apps', 'qgis-ltr')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(QGIS_PATH, 'apps', 'Qt5', 'plugins')

# ----------------------------------------------------------------------------------
# 🚀 Initialize QGIS
# ----------------------------------------------------------------------------------
from qgis.core import QgsApplication

QgsApplication.setPrefixPath(os.environ['QGIS_PREFIX_PATH'], True)
qgs = QgsApplication([], False)
qgs.initQgis()

print("✅ QGIS initialized successfully with Python 3.12!")

# ----------------------------------------------------------------------------------
# 🚀 Initialize QGIS
# ----------------------------------------------------------------------------------
# Necessary imports
from qgis.core import QgsApplication

# Starts the qgis application without the graphical user interface
gui_flag = False
app = QgsApplication([], gui_flag)
app.initQgis()

# Then you prepare the processing framework to access all default QGIS processing function
from processing.core.Processing import Processing
Processing.initialize()

from processing_umep.processing_umep_provider import ProcessingUMEPProvider
umep_provider = ProcessingUMEPProvider()
QgsApplication.processingRegistry().addProvider(umep_provider)

import processing

svf_output =  processing.run("umep:Urban Geometry: Sky View Factor",
                            {'INPUT_DSM':'C:/Users/Ardo/Desktop/thesis/processed/width15_deg030_h15to15/dsm.tif',
                             'INPUT_CDSM':None,
                             'TRANS_VEG':3,
                             'INPUT_TDSM':None,
                             'INPUT_THEIGHT':25,
                             'ANISO':True,
                             'WALL_SCHEME':False,
                             'KMEANS':True,
                             'CLUSTERS':5,
                             'INPUT_DEM':None,
                             'INPUT_SVFHEIGHT':1,
                             'OUTPUT_DIR':'C:/Users/Ardo/Desktop/thesis/processed/width15_deg030_h15to15',
                             'OUTPUT_FILE':'C:/Users/Ardo/Desktop/thesis/processed/width15_deg030_h15to15/svf.tif'})

"""wallHeightRatio_outputs =   processing.run("umep:Urban Geometry: Wall Height and Aspect",
                                           {'INPUT':'C:/Users/Andrea/Desktop/thesis/rotated_json/dsm_000deg.tif',
                                            'INPUT_LIMIT':3,
                                            'OUTPUT_HEIGHT':'C:/Users/Andrea/Desktop/thesis/rotated_json/WallH_000deg.tif',
                                            'OUTPUT_ASPECT':'C:/Users/Andrea/Desktop/thesis/rotated_json/WallR_000deg.tif'})
"""
"""mrt_output =  processing.run("umep:Outdoor Thermal Comfort: SOLWEIG",
                             {'INPUT_DSM':'C:/Users/Andrea/Desktop/thesis/rotated_json/dsm_000deg.tif',
                              'INPUT_SVF':'C:\\Users\\Andrea\\Desktop\\thesis\\rotated_json\\svf_000deg\\svfs.zip',
                              'INPUT_HEIGHT':'C:/Users/Andrea/Desktop/thesis/rotated_json/WallH_000deg.tif',
                              'INPUT_ASPECT':'C:/Users/Andrea/Desktop/thesis/rotated_json/WallR_000deg.tif',
                              'INPUT_CDSM':None,
                              'TRANS_VEG':3,
                              'LEAF_START':97,
                              'LEAF_END':300,
                              'CONIFER_TREES':False,
                              'INPUT_TDSM':None,
                              'INPUT_THEIGHT':25,
                              'INPUT_LC':None,
                              'USE_LC_BUILD':False,
                              'INPUT_DEM':'C:/Users/Andrea/Desktop/thesis/rotated_json/dem_000deg.tif',
                              'SAVE_BUILD':True,
                              'INPUT_ANISO':'',
                              'INPUT_WALLSCHEME':'',
                              'WALLTEMP_NETCDF':False,
                              'WALL_TYPE':0,
                              'ALBEDO_WALLS':0.2,
                              'ALBEDO_GROUND':0.15,
                              'EMIS_WALLS':0.9,
                              'EMIS_GROUND':0.95,
                              'ABS_S':0.7,
                              'ABS_L':0.95,
                              'POSTURE':0,
                              'CYL':True,
                              'INPUTMET':'C:\\Users\\Andrea\\Desktop\\thesis\\BCN_map\\Climate\\climate_BCN_17Jul.txt',
                              'ONLYGLOBAL':True,
                              'UTC':1,
                              'WOI_FILE':None,
                              'WOI_FIELD':'',
                              'POI_FILE':None,
                              'POI_FIELD':'',
                              'AGE':35,
                              'ACTIVITY':80,
                              'CLO':0.9,
                              'WEIGHT':75,
                              'HEIGHT':180,
                              'SEX':0,
                              'SENSOR_HEIGHT':10,
                              'OUTPUT_TMRT':True,
                              'OUTPUT_KDOWN':False,
                              'OUTPUT_KUP':False,
                              'OUTPUT_LDOWN':False,
                              'OUTPUT_LUP':False,
                              'OUTPUT_SH':True,
                              'OUTPUT_TREEPLANTER':False,
                              'OUTPUT_DIR':'C:\\Users\\Andrea\\Desktop\\thesis\\rotated_json\\mrt_000deg'})"""

#utci_output = 

"""solarRadiation_output =  processing.run("umep:Solar Radiation: Shadow Generator",
                                        {'INPUT_DSM':'C:/Users/Andrea/Desktop/thesis/rotated_json/dsm_000deg.tif',
                                         'INPUT_CDSM':None,
                                         'TRANS_VEG':3,
                                         'INPUT_TDSM':None,
                                         'INPUT_THEIGHT':25,
                                         'INPUT_HEIGHT':'C:/Users/Andrea/Desktop/thesis/rotated_json/WallH_000deg.tif',
                                         'INPUT_ASPECT':'C:/Users/Andrea/Desktop/thesis/rotated_json/WallR_000deg.tif',
                                         'UTC':15,
                                         'DST':False,
                                         'DATEINI':QDate(2025, 8, 5),
                                         'ITERTIME':30,
                                         'ONE_SHADOW':False,
                                         'TIMEINI':QTime(18, 3, 1),
                                         'OUTPUT_DIR':'C:\\Users\\Andrea\\Desktop\\thesis\\rotated_json\\shadow_000deg',
                                         'OUTPUT_FILE':'C:/Users/Andrea/Desktop/thesis/rotated_json/shadow_000deg/shadow_000deg.tif'})"""


# ----------------------------------------------------------------------------------
# 🧹 Clean exit
# ----------------------------------------------------------------------------------
qgs.exitQgis()
