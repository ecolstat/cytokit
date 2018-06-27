from codex.ops.op import CodexOp
from os import path as osp
import codex
from codex import io as codex_io
import numpy as np
import logging

logger = logging.getLogger(__name__)

TILE_GEN_MODE_RAW = 'raw'
TILE_GEN_MODE_STACK = 'stack'
TILE_GEN_MODES = [TILE_GEN_MODE_RAW, TILE_GEN_MODE_STACK]


def _validate_mode(mode):
    if mode not in TILE_GEN_MODES:
        raise ValueError('Tile generator mode must be one of {} not "{}"'.format(TILE_GEN_MODES, mode))


class CodexTileGenerator(CodexOp):

    def __init__(self, config, data_dir, region_index, tile_index, mode='raw',
                 raw_file_type=codex.FT_GRAYSCALE, path_fmt_name=codex_io.FMT_PROC_IMAGE):
        super(CodexTileGenerator, self).__init__(config)
        self.data_dir = data_dir
        self.mode = mode
        self.region_index = region_index
        self.tile_index = tile_index
        self.raw_file_type = config.tile_generator_params.get('raw_file_type', raw_file_type)
        self.path_fmt_name = path_fmt_name
        _validate_mode(self.mode)

    def _run(self, *args, **kwargs):
        ncyc, nz, nch = self.config.n_cycles, self.config.n_z_planes, self.config.n_channels_per_cycle

        _validate_mode(self.mode)

        # If in "raw" mode, load a tile by accumlating individual grayscale images
        if self.mode == 'raw':
            # Tile should have shape (cycles, z, channel, height, width)
            img_cyc = []
            for icyc in range(ncyc):
                img_ch = []
                for ich in range(nch):
                    img_z = []
                    for iz in range(nz):
                        img_path = codex_io.get_raw_img_path(self.region_index, self.tile_index, icyc, ich, iz)
                        img_path = osp.join(self.data_dir, img_path)
                        img = codex_io.read_raw_microscope_image(img_path, self.raw_file_type)
                        if img.ndim != 2:
                            raise ValueError(
                                'Expecting raw image at path "{}" to have 2 dims but found shape {}'
                                .format(img_path, img.shape)
                            )
                        img_z.append(img)
                    img_ch.append(np.stack(img_z, 0))
                img_cyc.append(np.stack(img_ch, 1))
            tile = np.stack(img_cyc, 0)

        # Otherwise assume that the tile has already been assembled and just read it in instead
        else:
            tx, ty = self.config.get_tile_coordinates(self.tile_index)
            img_path = codex_io.get_img_path(self.path_fmt_name, self.region_index, tx, ty)
            tile = codex_io.read_tile(osp.join(self.data_dir, img_path), self.config)

        return tile
