# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2015 - Qingfeng Xia <qingfeng.xia()eng.ox.ac.uk>        *
# *   Copyright (c) 2017 Alfred Bogaers (CSIR) <abogaers@csir.co.za>        *
# *   Copyright (c) 2017 Oliver Oxtoby (CSIR) <ooxtoby@csir.co.za>          *
# *   Copyright (c) 2017 Johan Heyns (CSIR) <jheyns@csir.co.za>             *
# *   Copyright (c) 2019 Oliver Oxtoby <oliveroxtoby@gmail.com>             *
# *   Copyright (c) 2022 Jonathan Bergh <bergh.jonathan@gmail.com>          *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

from __future__ import print_function

import FreeCAD
import CfdTools
import CfdAnalysis
from PySide.QtCore import QObject, Signal
from CfdResidualPlot import ResidualPlot
from collections import OrderedDict
from core.plotters.CfdForcesPlot import ForcesPlot
from core.plotters.CfdForceCoeffPlot import ForceCoeffsPlot

class CfdRunnable(QObject, object):

    def __init__(self, analysis=None, solver=None):
        super(CfdRunnable, self).__init__()

        if analysis and isinstance(analysis.Proxy, CfdAnalysis._CfdAnalysis):
            self.analysis = analysis
        else:
            if FreeCAD.GuiUp:
                self.analysis = CfdTools.getActiveAnalysis()

        self.solver = None
        if solver:
            self.solver = solver
        else:
            if analysis:
                self.solver = CfdTools.getSolver(self.analysis)
            if not self.solver:
                FreeCAD.Console.printMessage("Solver object is missing from Analysis Object")

        if self.analysis:
            self.results_present = False
            self.result_object = None
        else:
            raise Exception('No active analysis found')

    def check_prerequisites(self):
        return ""


class CfdRunnableFoam(CfdRunnable):
    update_residual_signal = Signal(list, list, list, list)

    def __init__(self, analysis=None, solver=None):
        super(CfdRunnableFoam, self).__init__(analysis, solver)

        self.residual_plotter = None
        self.forces_plotter = None
        self.force_coeffs_plotter = None
        self.forces_plot = False
        self.force_coeffs_plot = False

        analysis_obj = CfdTools.getActiveAnalysis()
        function_objs = CfdTools.getFunctionObjectsGroup(analysis_obj)
        if function_objs is not None:
            for fo_type in function_objs:
                if fo_type.FunctionObjectType == "Force":
                    self.forces_plot = True
                elif fo_type.FunctionObjectType == "ForceCoefficients":
                    self.force_coeffs_plot = True

        self.initResiduals()
        self.initMonitors()

    def check_prerequisites(self):
        return ""

    def initResiduals(self):
        self.UxResiduals = []
        self.UyResiduals = []
        self.UzResiduals = []
        self.pResiduals = []
        self.rhoResiduals = []
        self.EResiduals = []
        self.kResiduals = []
        self.epsilonResiduals = []
        self.omegaResiduals = []
        self.nuTildaResiduals = []
        self.gammaIntResiduals = []
        self.ReThetatResiduals = []
        self.niter = 0

    def initMonitors(self):
        self.pressureXResiduals = []
        self.pressureYResiduals = []
        self.pressureZResiduals = []

        self.viscousXResiduals = []
        self.viscousYResiduals = []
        self.viscousZResiduals = []

        self.cdResiduals = []
        self.clResiduals = []

    def get_solver_cmd(self, case_dir):
        self.initResiduals()
        self.initMonitors()

        self.residual_plotter = ResidualPlot()

        if self.forces_plot:
            self.forces_plotter = ForcesPlot()

        if self.force_coeffs_plot:
            self.force_coeffs_plotter = ForceCoeffsPlot()

        # Environment is sourced in run script, so no need to include in run command
        cmd = CfdTools.makeRunCommand('./Allrun', case_dir, source_env=False)
        FreeCAD.Console.PrintMessage("Solver run command: " + ' '.join(cmd) + "\n")
        return cmd

    def getRunEnvironment(self):
        return CfdTools.getRunEnvironment()

    def process_output(self, text):
        log_lines = text.split('\n')
        for line in log_lines:
            # print line,
            split = line.split()

            # Only store the first residual per timestep
            if line.startswith(u"Time = "):
                self.niter += 1

            # print split
            if "Ux," in split and self.niter-1 > len(self.UxResiduals):
                self.UxResiduals.append(float(split[7].split(',')[0]))
            if "Uy," in split and self.niter-1 > len(self.UyResiduals):
                self.UyResiduals.append(float(split[7].split(',')[0]))
            if "Uz," in split and self.niter-1 > len(self.UzResiduals):
                self.UzResiduals.append(float(split[7].split(',')[0]))
            if "p," in split and self.niter-1 > len(self.pResiduals):
                self.pResiduals.append(float(split[7].split(',')[0]))
            if "p_rgh," in split and self.niter-1 > len(self.pResiduals):
                self.pResiduals.append(float(split[7].split(',')[0]))
            if "h," in split and self.niter-1 > len(self.EResiduals):
                self.EResiduals.append(float(split[7].split(',')[0]))
            # HiSA coupled residuals
            if "Residual:" in split and self.niter-1 > len(self.rhoResiduals):
                self.rhoResiduals.append(float(split[4]))
                self.UxResiduals.append(float(split[5].lstrip('(')))
                self.UyResiduals.append(float(split[6]))
                self.UzResiduals.append(float(split[7].rstrip(')')))
                self.EResiduals.append(float(split[8]))
            if "k," in split and self.niter-1 > len(self.kResiduals):
                self.kResiduals.append(float(split[7].split(',')[0]))
            if "epsilon," in split and self.niter - 1 > len(self.epsilonResiduals):
                self.epsilonResiduals.append(float(split[7].split(',')[0]))
            if "omega," in split and self.niter-1 > len(self.omegaResiduals):
                self.omegaResiduals.append(float(split[7].split(',')[0]))
            if "nuTilda," in split and self.niter-1 > len(self.nuTildaResiduals):
                self.nuTildaResiduals.append(float(split[7].split(',')[0]))
            if "gammaInt," in split and self.niter-1 > len(self.gammaIntResiduals):
                self.gammaIntResiduals.append(float(split[7].split(',')[0]))
            if "ReThetat," in split and self.niter-1 > len(self.ReThetatResiduals):
                self.ReThetatResiduals.append(float(split[7].split(',')[0]))

            # Force monitors
            if "Pressure" in split and self.niter-1 > len(self.pressureXResiduals):
                self.pressureXResiduals.append(float(split[2].replace("(", "")))
                self.pressureYResiduals.append(float(split[3]))
                self.pressureZResiduals.append(float(split[4].replace(")", "")))

            if "Viscous" in split and self.niter-1 > len(self.viscousXResiduals):
                self.viscousXResiduals.append(float(split[2].replace("(", "")))
                self.viscousYResiduals.append(float(split[3]))
                self.viscousZResiduals.append(float(split[4].replace(")", "")))

            # Force coefficient monitors
            if "Cd" in split and self.niter-1 > len(self.cdResiduals):
                self.cdResiduals.append(float(split[2]))
            if "Cl" in split and self.niter-1 > len(self.clResiduals):
                self.clResiduals.append(float(split[2]))

        if self.niter > 1:
            self.residual_plotter.updateResiduals(OrderedDict([
                ('$\\rho$', self.rhoResiduals),
                ('$U_x$', self.UxResiduals),
                ('$U_y$', self.UyResiduals),
                ('$U_z$', self.UzResiduals),
                ('$p$', self.pResiduals),
                ('$E$', self.EResiduals),
                ('$k$', self.kResiduals),
                ('$\\epsilon$', self.epsilonResiduals),
                ('$\\tilde{\\nu}$', self.nuTildaResiduals),
                ('$\\omega$', self.omegaResiduals),
                ('$\\gamma$', self.gammaIntResiduals),
                ('$Re_{\\theta}$', self.ReThetatResiduals)]))

            self.forces_plotter.updateResiduals(OrderedDict([
                ('$Pressure_x$', self.pressureXResiduals),
                ('$Pressure_y$', self.pressureYResiduals),
                ('$Pressure_z$', self.pressureZResiduals),
                ('$Viscous_x$', self.viscousXResiduals),
                ('$Viscous_y$', self.viscousYResiduals),
                ('$Viscous_z$', self.viscousZResiduals)]))

            self.force_coeffs_plotter.updateResiduals(OrderedDict([
                ('$C_D$', self.cdResiduals),
                ('$C_L$', self.clResiduals)
            ]))
