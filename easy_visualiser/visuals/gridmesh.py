import numpy as np
from vispy.geometry import create_grid_mesh
from vispy.scene.visuals import create_visual_node
from vispy.visuals import MeshVisual
from vispy.visuals.gridmesh import GridMeshVisual


class FixedGridMeshVisual(GridMeshVisual):
    def set_data(self, xs=None, ys=None, zs=None, colors=None, filter_nan=True):
        """Update the mesh data.

        Parameters
        ----------
        xs : ndarray | None
            A 2d array of x coordinates for the vertices of the mesh.
        ys : ndarray | None
            A 2d array of y coordinates for the vertices of the mesh.
        zs : ndarray | None
            A 2d array of z coordinates for the vertices of the mesh.
        colors : ndarray | None
            The color at each point of the mesh. Must have shape
            (width, height, 4) or (width, height, 3) for rgba or rgb
            color definitions respectively.
        """
        if xs is None:
            xs = self._xs
            GridMeshVisual._GridMeshVisual__vertices = None

        if ys is None:
            ys = self._ys
            self._GridMeshVisual__vertices = None

        if zs is None:
            zs = self._zs
            self._GridMeshVisual__vertices = None

        if self._GridMeshVisual__vertices is None:
            self._xs = xs
            self._ys = ys
            self._zs = zs
            vertices, indices = create_grid_mesh(self._xs, self._ys, self._zs)

            # Flip the normal every 2nd index
            indices[1::2, :] = indices[1::2, ::-1]

            if filter_nan:
                # get all vertices that contains nan
                nan_vertices = np.any(np.isnan(vertices), axis=1)
                # set them to default value
                # NOTE: we do not remove them from the array, because the faces/indices array
                #       reference those indices.
                #       - if we remove them, the indices will be changed.
                #       - on the other hand, if we remain those nan values, the open-gl will
                #         exhibit some weird behaviour (not crashing, but behave strangely)
                #       - if the face indices do not reference the vertices, their actual value
                #         "shouldn't" matters.
                vertices[np.any(np.isnan(vertices), axis=1)] = 0

                # put the vertices into indices
                invalid_vertex_indices = np.unique(np.where(nan_vertices))
                # filter out face indices
                indices = indices[
                    np.all(
                        np.isin(indices, invalid_vertex_indices, invert=True), axis=1
                    )
                ]

            self._GridMeshVisual__meshdata.set_vertices(vertices)
            self._GridMeshVisual__meshdata.set_faces(indices)

        if colors is not None:
            self._GridMeshVisual__meshdata.set_vertex_colors(
                colors.reshape(colors.shape[0] * colors.shape[1], colors.shape[2])
            )

        MeshVisual.set_data(self, meshdata=self._GridMeshVisual__meshdata)


FixedGridMesh = create_visual_node(FixedGridMeshVisual)

__all__ = ["FixedGridMesh"]
