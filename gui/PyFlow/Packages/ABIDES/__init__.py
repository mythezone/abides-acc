import os
from PyFlow.Core.PackageBase import PackageBase

class ABIDES(PackageBase):
	def __init__(self):
		super(ABIDES, self).__init__()
		self.analyzePackage( os.path.dirname(__file__))