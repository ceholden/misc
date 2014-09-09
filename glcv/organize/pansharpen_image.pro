PRO pansharpen_image, hires_file, lores_file, out_file, sensor_id
	COMPILE_OPT IDL2, HIDDEN

	print, 'Hires: ', hires_file
	print, 'Lores: ', lores_file
	print, 'Output: ', out_file

	;; open envi for processing files
	envi
	envi_batch_init
	
	;; open the files that will be processed
	;; exit on error
	envi_open_file,hires_file,r_fid = hires_fid
	if(hires_fid eq -1) then begin
		print, 'could not open hires file'
		print, hires_file
		envi_batch_exit
		return
	endif
	envi_open_file,lores_file,r_fid = lores_fid
	if(lores_fid eq -1) then begin
		print, 'could not open lores file'
		envi_batch_exit
		return
	endif
	
	;; query files for the necessary parameters
	envi_file_query, hires_fid, ns=ns_hi, nl=nl_hi, nb=nb_hi, dims=dims_hi
	envi_file_query, lores_fid, ns=ns_low, nl=nl_low, nb=nb_low, dims=dims_low

	pos_hi = lindgen(nb_hi)
	pos_low = lindgen(nb_low)

	;; output params
	dims_out = dims_low
	pos_out = pos_low
	print, 'Output bands: ', pos_out

	; print,hires_file,hires_fid,ns_hi,nl_hi,nb_hi,dims_hi
	; print,lores_file,lores_fid,ns_low,nl_low,nb_low,dims_low

	print, 'Done loading inputs'
	
	;; get the appropriate spectral library
	; Quickbird
	if (sensor_id eq 1) then begin
		sli_file = '/net/usr/local/itt-4.8/idl/idl80/products/envi48/filt_func/quickbird.sli'
	; Worldview-2
	endif else if (sensor_id eq 2) then begin
		sli_file = '/net/usr/local/itt-4.8/idl/idl80/products/envi48/filt_func/worldview2.sli'
	; Orbview-3 has no SLI file
	endif else if (sensor_id eq 3) then begin
		sli_file = ''
	; Ikonos
	endif else if (sensor_id eq 4) then begin
		sli_file = '/net/usr/local/itt-4.8/idl/idl80/products/envi48/filt_func/ikonos.sli'
	endif else begin
		print, 'unknown sensor id ',sensor_id
		envi_batch_exit
		return
	endelse
	
	; If we're not working on an Orbview, open SLI file
	if (sensor_id ne 3) then begin
		; Open the file
		envi_open_file, sli_file, r_fid=sli_fid
		if(sli_fid eq -1) then begin
			envi_batch_exit
			print, 'could not open the sli file'
			return
		endif
		; Get file dimensions and names of spectra
		envi_file_query, sli_fid, spec_names=spec_names, $
				ns=sli_ns, nl=sli_nl,file_type=sli_type
		print,spec_names,sli_ns,sli_nl,sli_type
	endif
	
	; If Orbview, use method 0 option
	; this creates a psh file with the method=0 option
	if (sensor_id eq 3) then begin
		envi_doit, 'envi_gs_sharpen_doit', fid=lores_fid, $
			dims=dims_low, pos=pos_out, method=0, interp=2, $
			out_name=out_file, hires_fid=hires_fid, $ 
			hires_dims=dims_hi
	endif else begin
        ; this creates a psh file with the method=2 option
		envi_doit, 'envi_gs_sharpen_doit', fid=lores_fid, $
			dims=dims_low, pos=pos_out, method=2, interp=2, $
			out_name=out_file, hires_fid=hires_fid, $ 
			hires_dims=dims_hi, filter_fid=sli_fid,filter_pos=0
	endelse	
	;; close any open files
	close,/all
	
;	print, 'done with envi'
	;; exit out of envi batch mode and return null
	envi_batch_exit,/no_confirm

return
END
