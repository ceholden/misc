library(raster)
library(maptools)
library(rgdal)

remove(list=ls())

wd='/home/ceholden/Documents/sub_3'
setwd(wd)

# Grab our RGBNIR image
image<-brick(list.files(pattern='img_sub')[1])
extent<-extent(image)
# Find regionmaps
armaps<-list.files(pattern='regionmap',recursive=T)
# Eliminate header files, regionmap_poly*
armaps<-armaps[seq(1,length(armaps),by=6)]
# Find regionmap shapefiles
armaps_shp<-list.files(pattern='regionmap_poly.shp',recursive=T)

# START GRAPHING
set.seed(10)

looksize=25
xrange<-extent@xmax-extent@xmin
yrange<-extent@ymax-extent@ymin
looks=floor(min(xrange,yrange)/looksize)
# Loop through subsets of our subset image
for (i in 1:looks) {
    pdf(file=paste('subsets_areas-',i,'.pdf'),height=11,width=8.5)
    par(xaxs="i",yaxs="i",mfrow=c(2,1),oma=c(1,1,1,1))
                      
    xstart<-extent@xmin+looksize*(i-1)
    ystart<-floor(runif(1,min=extent@ymin+looksize+25,max=extent@ymax-looksize-25))
    
    limx<-c(xstart,xstart+looksize)
    limy<-c(ystart,ystart+looksize)
    ext<-rbind(limx,limy)
        
    plotRGB(image,r=4,g=3,b=1,ext=ext,main='Image',stretch='hist')
    # Loop through 
    for (j in 1:length(armaps)) {
      title=unlist(strsplit(armaps[j],"/"))[1]
      plotRGB(image,r=3,g=2,b=1,ext=ext,main=title,stretch='hist')
      shp<-readOGR(armaps_shp[j],layer='regionmap_poly')
      plot(shp,xlim=limx,ylim=limy,add=T,border='red',lwd=0.5)
      rm(shp)
    }
    dev.off()
    print(paste('Finished parameter sequence ',i))
}
