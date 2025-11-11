option solver gurobi;
# Quitar bestbound 1 y añadir NodefileStart para usar disco en caso de faltar RAM
option gurobi_options 'outlev=1 mipgap 0.01 logfile "./logfile.txt" NodefileStart=1.0 NodefileDir="."';

param cli;
param loc;
param ICap{1 .. loc};
param FC{1 .. loc};
param dem{1 .. cli};
param TC{1 .. cli, 1 .. loc};

var x {1 .. loc} binary;
var y {1 .. cli, 1 .. loc} binary;

minimize Total_Cost: ((sum {j in 1..loc} x[j] * FC[j])) + ((sum {j in 1..loc} (sum {i in 1..cli} y[i,j] * TC[i,j]))) ;

s.t.			 
						
	allocation1 {i in 1..cli}:    	sum {j in 1..loc} y[i,j] = 1;

	capacity {j in 1..loc}: sum {i in 1..cli} dem[i]*y[i,j] <= ICap[j]*x[j];
	
	enlace {i in 1..cli, j in 1..loc}: y[i,j] <= x[j]; # Cliente i se asigna a loc j solo si loc j esta abierto
