library(Cardinal)
library(CardinalWorkflows)
library(ggplot2)

path_processed = '/Users/josephmonaghan/Documents/Data for imzML paper/Candidate Pretty Images/Kiera/Brain no Li/Brain_no_Li/Brain_no_Li_FTMS + p ESI Full ms [70.0000-1000.imzML'
aspect <- 150 / 15.725335253218892


msa = readMSIData(path_processed)

norm = normalize(msa,method="rms")
msa_peaks = peakAlign(norm,tolerance=10,units="ppm")
msa_filt <- subsetFeatures(msa_peaks,freq > 0.1)

image(msa_filt,mz=175.1190,enhance="adapt",asp=aspect)
ssc <- spatialShrunkenCentroids(msa_filt,r=1,k=2,s=0)


mask <- ssc@model[["probability"]]
mask_omits <- as.logical(mask[,2])

msa_masked <- msa_filt[!mask_omits]

layout.matrix <- matrix(c(0,1,2,3), nrow=2,ncol=2)
layout(mat=layout.matrix,
       heights=c(1,2),
       widths=c(2,2))
image(ssc, k=2, type="probability",asp=150/14)
plot(ssc,i=1,type='centers',linewidth=2,superpose=FALSE,layout=c(2,1))


cropped_var_seg <- spatialShrunkenCentroids(msa_masked,r=1,k=c(3,4,5,6,7,8,9),s=0)


image(cropped_var_seg,i=3,type="probability",asp=aspect)
plot(cropped_var_seg,i=7,type='centers',linewidth=2,superpose=FALSE,layout=c(4,2))


