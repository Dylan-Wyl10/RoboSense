#####################################
06/05/2023 YW: this directory is for generate od trip file to get routing file for simulation.
 - tax_all.taz.xml: all taz for 6x6 grid network. including taz_id and edge_id
 - od_file.od: od file to determine the flow for the network. it could be written by run the script: gen_od.sh
 
 ##########################################
 10/30/2023 YW: update the path and project structure. 
 - 1.remove the sumo configurations under root path. The OD generator need to run seperately.
 - 2.Two steps are required: after step 1, the user need to combine cav.trip into bgv.trip manually.
