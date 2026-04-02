from DirFluxParser import OrdemParser

parser = OrdemParser()
result = parser.parse_file("ORDEM/DIRFLUX_SC.OUT")

print(result.year)
print(result.total_flux(">1cm"))
print(result.total_flux(">10cm"))
print(result.band_flux(">1cm", ">10cm"))