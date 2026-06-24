import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Row, Col, Divider, DatePicker, InputNumber, Space, Button, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import moment from 'moment';
import { getOrganizations, createOrganization } from '../../api/organizations';
import { getFilters } from '../../api/cases';
import { getFormOptions } from '../../api/entry';

const { TextArea } = Input;

const officeMapping = {
  "cn Đà Nẵng": ["vp Đà Nẵng"],
  "cn Miền Bắc": ["vp Hưng Yên", "vp Hải Phòng", "vp Hà Nam Ninh", "vp Hà Nội", "vp Nghệ An", "vp Thái Nguyên"],
  "CN Miền Nam": ["vp Cần Thơ", "vp HCM", "vp Đồng Nai", "vp Bình Dương"]
};

const formatContractNumber = (value) => {
  if (!value) return value;
  const val = value.trim();
  const currentYear = new Date().getFullYear();
  const currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');
  
  if (/^\d{4}$/.test(val)) {
    return `010/${currentYear}/N${currentMonth}-${val}/DN`;
  }
  if (/^\.\d{4}$/.test(val)) {
    return `010/${currentYear}/N${currentMonth}.${val.substring(1)}/DN`;
  }
  return value;
};

export default function CaseEditModal({ open, caseData, onCancel, onSave, filterOptions = {} }) {
  const [form] = Form.useForm();
  const customerType = Form.useWatch('customer_type', form);
  const selectedBranch = Form.useWatch('valuation_branch', form);
  const isEdit = !!caseData?.id;

  const [organizations, setOrganizations] = useState([]);
  const [newOrgOpen, setNewOrgOpen] = useState(false);
  const [newOrgForm] = Form.useForm();

  const [customPurposes, setCustomPurposes] = useState([]);
  const [customAssetTypes, setCustomAssetTypes] = useState([]);
  const [customBranches, setCustomBranches] = useState([]);
  const [customOffices, setCustomOffices] = useState([]);
  const [internalFilters, setInternalFilters] = useState({});

  useEffect(() => {
    if (open) {
      Promise.allSettled([
        getFilters(),
        getFormOptions()
      ]).then(([filtersRes, optionsRes]) => {
        const filters = filtersRes.status === 'fulfilled' ? (filtersRes.value.data || {}) : {};
        const options = optionsRes.status === 'fulfilled' ? (optionsRes.value.data || {}) : {};
        
        setInternalFilters({
          branches: [...new Set([...(options.source || []), ...(filters.branches || [])])],
          appraisers: [...new Set([...(options.valuation_staff || []), ...(filters.appraisers || [])])],
          payment_statuses: filters.payment_statuses && filters.payment_statuses.length ? filters.payment_statuses : ['Đã thanh toán', 'Chưa thanh toán'],
          offices: ['vp Đà Nẵng'],
          valuation_purposes: [...new Set([...(options.valuation_purpose || []), ...(filters.valuation_purposes || [])])],
          asset_types: [...new Set([...(options.asset_type || []), ...(filters.asset_types || [])])],
        });
      }).catch(err => {
        console.error("Error loading filters/options in CaseEditModal:", err);
      });
    }
  }, [open]);

  // Fetch organizations when modal opens
  useEffect(() => {
    if (open) {
      getOrganizations()
        .then(res => setOrganizations(res.data || []))
        .catch(err => console.error(err));
    }
  }, [open]);

  const handleOrgSelect = (value) => {
    const org = organizations.find(o => o.id === value);
    if (org) {
      form.setFieldsValue({
        customer_info: org.name || '',
        customer_address: org.address || '',
        tax_code: org.tax_code || '',
        representative_name: org.representative || '',
        representative_position: org.position || '',
      });
    }
  };

  const handleCreateOrgSubmit = async (values) => {
    try {
      const res = await createOrganization({
        name: values.name.trim(),
        address: values.address || '',
        tax_code: values.tax_code || '',
        representative: values.representative || '',
        position: values.position || '',
      });
      message.success('Thêm tổ chức mới thành công! 🏢');
      setNewOrgOpen(false);
      newOrgForm.resetFields();
      
      // Reload list
      const newOrgsRes = await getOrganizations();
      const newOrgs = newOrgsRes.data || [];
      setOrganizations(newOrgs);
      
      // Auto select and fill in edit form
      form.setFieldsValue({
        customer_info: values.name.trim(),
        customer_address: values.address || '',
        tax_code: values.tax_code || '',
        representative_name: values.representative || '',
        representative_position: values.position || '',
      });
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Thêm tổ chức thất bại');
    }
  };

  const handleAddNewPurpose = () => {
    let inputVal = '';
    Modal.confirm({
      title: 'Thêm mới Mục đích thẩm định',
      icon: <PlusOutlined style={{ color: '#0f6cbd' }} />,
      content: (
        <Input 
          placeholder="Nhập mục đích mới..." 
          onChange={(e) => { inputVal = e.target.value; }} 
          style={{ marginTop: 12 }}
        />
      ),
      okText: 'Thêm',
      cancelText: 'Hủy',
      onOk: () => {
        const val = inputVal.trim();
        if (val) {
          setCustomPurposes(prev => [...prev, val]);
          form.setFieldValue('valuation_purpose', val);
        }
      }
    });
  };

  const handleAddNewAssetType = () => {
    let inputVal = '';
    Modal.confirm({
      title: 'Thêm mới Loại tài sản',
      icon: <PlusOutlined style={{ color: '#0f6cbd' }} />,
      content: (
        <Input 
          placeholder="Nhập loại tài sản mới..." 
          onChange={(e) => { inputVal = e.target.value; }} 
          style={{ marginTop: 12 }}
        />
      ),
      okText: 'Thêm',
      cancelText: 'Hủy',
      onOk: () => {
        const val = inputVal.trim();
        if (val) {
          setCustomAssetTypes(prev => [...prev, val]);
          form.setFieldValue('asset_type', val);
        }
      }
    });
  };

  const handleAddNewBranch = () => {
    let inputVal = '';
    Modal.confirm({
      title: 'Thêm mới Chi nhánh / Ngân hàng nguồn',
      icon: <PlusOutlined style={{ color: '#0f6cbd' }} />,
      content: (
        <Input 
          placeholder="Nhập chi nhánh/ngân hàng mới..." 
          onChange={(e) => { inputVal = e.target.value; }} 
          style={{ marginTop: 12 }}
        />
      ),
      okText: 'Thêm',
      cancelText: 'Hủy',
      onOk: () => {
        const val = inputVal.trim();
        if (val) {
          setCustomBranches(prev => [...prev, val]);
          form.setFieldValue('source', val);
        }
      }
    });
  };

  const handleAddNewOffice = () => {
    let inputVal = '';
    Modal.confirm({
      title: 'Thêm mới Văn phòng thẩm định',
      icon: <PlusOutlined style={{ color: '#0f6cbd' }} />,
      content: (
        <Input 
          placeholder="Nhập tên văn phòng mới..." 
          onChange={(e) => { inputVal = e.target.value; }} 
          style={{ marginTop: 12 }}
        />
      ),
      okText: 'Thêm',
      cancelText: 'Hủy',
      onOk: () => {
        const val = inputVal.trim();
        if (val) {
          setCustomOffices(prev => [...prev, val]);
          form.setFieldValue('office', val);
        }
      }
    });
  };

  const {
    branches = [],
    appraisers = [],
    payment_statuses = ['Đã thanh toán', 'Chưa thanh toán'],
    offices = ['vp Đà Nẵng'],
    valuation_purposes = [],
    asset_types = []
  } = { ...internalFilters, ...filterOptions };

  const statuses = ['Đang xử lý', 'Hoàn thành', 'Hủy'];

  // Initialize form values when modal opens or caseData changes
  useEffect(() => {
    if (open) {
      if (caseData) {
        form.setFieldsValue({
          ...caseData,
          // Convert date strings to moment if needed, but since we use standard inputs for simplicity and compatibility, string is fine.
          // However, if we want text inputs for date we can just use normal Input!
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          case_status: 'Đang xử lý',
          payment_status: 'Chưa thanh toán',
          customer_type: 'individual',
          asset_type: 'BĐS đặc thù khác',
          execution_month: moment().format('MM/YYYY')
        });
      }
    }
  }, [open, caseData, form]);

  const handleSubmit = () => {
    form.validateFields()
      .then(values => {
        onSave(values);
      })
      .catch(info => {
        console.log('Validate Failed:', info);
      });
  };

  return (
    <>
      <Modal
        open={open}
      title={isEdit ? `Sửa hồ sơ: ${caseData.contract_number || 'Chưa có số HĐ'}` : 'Thêm hồ sơ mới'}
      okText="Lưu"
      cancelText="Hủy"
      onCancel={onCancel}
      onOk={handleSubmit}
      width={900}
      style={{ top: 20 }}
    >
      <Form
        form={form}
        layout="vertical"
        name="case_form"
        initialValues={{
          case_status: 'Đang xử lý',
          payment_status: 'Chưa thanh toán',
          asset_type: 'BĐS đặc thù khác'
        }}
      >
        {/* Section 1: Thông tin hợp đồng */}
        <Divider orientation="left" style={{ margin: '12px 0', color: '#0f6cbd' }}>Thông tin hợp đồng</Divider>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="contract_number" label="Số hợp đồng">
              <Input 
                placeholder="Ví dụ: 01/2026/HDTD" 
                onBlur={(e) => {
                  const formatted = formatContractNumber(e.target.value);
                  form.setFieldValue('contract_number', formatted);
                }}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="contract_date" label="Ngày hợp đồng">
              <Input placeholder="Ví dụ: 20/06/2026" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="certificate_date" label="Ngày phát hành chứng thư">
              <Input placeholder="Ví dụ: 23/06/2026" />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="source" label="Nguồn / Ngân hàng">
              <Select 
                showSearch
                placeholder="Chọn ngân hàng"
                allowClear
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <Divider style={{ margin: '4px 0' }} />
                    <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<PlusOutlined />} 
                        style={{ width: '100%', color: '#0f6cbd', fontWeight: 600 }}
                        onClick={handleAddNewBranch}
                      >
                        Thêm mới...
                      </Button>
                    </div>
                  </>
                )}
                options={[...branches, ...customBranches].map(b => ({ label: b, value: b }))}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="valuation_branch" label="Chi nhánh thẩm định">
              <Select 
                showSearch
                placeholder="Chọn chi nhánh..."
                allowClear
                onChange={(val) => {
                  const newOffices = officeMapping[val] || [];
                  form.setFieldsValue({ office: newOffices[0] || undefined });
                }}
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <Divider style={{ margin: '4px 0' }} />
                    <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<PlusOutlined />} 
                        style={{ width: '100%', color: '#0f6cbd', fontWeight: 600 }}
                        onClick={() => {
                          let inputVal = '';
                          Modal.confirm({
                            title: 'Thêm mới Chi nhánh thẩm định',
                            icon: <PlusOutlined style={{ color: '#0f6cbd' }} />,
                            content: (
                              <Input 
                                placeholder="Nhập tên chi nhánh mới..." 
                                onChange={(e) => { inputVal = e.target.value; }} 
                                style={{ marginTop: 12 }}
                              />
                            ),
                            okText: 'Thêm',
                            cancelText: 'Hủy',
                            onOk: () => {
                              const val = inputVal.trim();
                              if (val) {
                                setCustomBranches(prev => [...prev, val]);
                                form.setFieldValue('valuation_branch', val);
                              }
                            }
                          });
                        }}
                      >
                        Thêm mới...
                      </Button>
                    </div>
                  </>
                )}
                options={[...["cn Đà Nẵng", "cn Miền Bắc", "CN Miền Nam"], ...customBranches].map(b => ({ label: b, value: b }))}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="office" label="Văn phòng thẩm định">
              <Select 
                showSearch
                placeholder="Chọn văn phòng..."
                allowClear
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <Divider style={{ margin: '4px 0' }} />
                    <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<PlusOutlined />} 
                        style={{ width: '100%', color: '#0f6cbd', fontWeight: 600 }}
                        onClick={handleAddNewOffice}
                      >
                        Thêm mới...
                      </Button>
                    </div>
                  </>
                )}
                options={[
                  ...(officeMapping[selectedBranch] || offices),
                  ...customOffices
                ].map(o => ({ label: o, value: o }))}
              />
            </Form.Item>
          </Col>
        </Row>

        {/* Section 2: Thông tin khách hàng */}
        <Divider orientation="left" style={{ margin: '12px 0', color: '#0f6cbd' }}>Thông tin khách hàng</Divider>
        <Row gutter={16}>
          <Col span={24}>
            {customerType === 'organization' ? (
              <Form.Item name="customer_info" label="Tên công ty / tổ chức" rules={[{ required: true, message: 'Vui lòng chọn hoặc nhập tên tổ chức!' }]}>
                <Select
                  showSearch
                  placeholder="Chọn từ danh bạ..."
                  onChange={(val) => {
                    const org = organizations.find(o => o.name === val);
                    if (org) {
                      form.setFieldsValue({
                        customer_address: org.address || '',
                        tax_code: org.tax_code || '',
                        representative_name: org.representative || '',
                        representative_position: org.position || '',
                      });
                    }
                  }}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: '4px 0' }} />
                      <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                        <Button 
                          type="text" 
                          size="small" 
                          icon={<PlusOutlined />} 
                          style={{ width: '100%', color: '#0f6cbd', fontWeight: 600 }}
                          onClick={() => setNewOrgOpen(true)}
                        >
                          Thêm mới tổ chức...
                        </Button>
                      </div>
                    </>
                  )}
                  options={organizations.map(o => ({
                    value: o.name,
                    label: `${o.name} (${o.tax_code || ''})`
                  }))}
                />
              </Form.Item>
            ) : (
              <Form.Item name="customer_info" label="Tên khách hàng" rules={[{ required: true, message: 'Vui lòng nhập tên khách hàng!' }]}>
                <Input placeholder="Tên khách hàng" />
              </Form.Item>
            )}
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="customer_type" label="Loại khách hàng">
              <Select options={[
                { label: 'Cá nhân', value: 'individual' },
                { label: 'Tổ chức', value: 'organization' }
              ]} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="customer_phone" label="Số điện thoại">
              <Input placeholder="SĐT liên hệ" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="citizen_id" label="CCCD / MST">
              <Input placeholder="CCCD hoặc Mã số thuế" />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item name="customer_address" label="Địa chỉ liên hệ">
              <Input placeholder="Địa chỉ thường trú / liên hệ" />
            </Form.Item>
          </Col>
        </Row>

        {customerType === 'organization' && (
          <>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="tax_code" label="Mã số thuế">
                  <Input placeholder="Nhập mã số thuế..." />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="representative_name" label="Người đại diện pháp luật">
                  <Input placeholder="Họ tên người đại diện..." />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="representative_position" label="Chức vụ người đại diện">
                  <Input placeholder="Giám đốc, Chủ tịch..." />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item name="authorization_note" label="Ủy quyền đại diện (nếu có)">
                  <Input placeholder="Ví dụ: Giấy ủy quyền số..." />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="handover_contact_name" label="Người nhận bàn giao">
                  <Input placeholder="Họ tên người nhận..." />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="handover_contact_position" label="Chức vụ người nhận bàn giao">
                  <Input placeholder="Chức vụ..." />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="handover_contact_phone" label="SĐT người nhận bàn giao">
                  <Input placeholder="SĐT liên hệ..." />
                </Form.Item>
              </Col>
            </Row>
          </>
        )}

        {/* Section 3: Thông tin tài sản */}
        <Divider orientation="left" style={{ margin: '12px 0', color: '#0f6cbd' }}>Thông tin tài sản</Divider>
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item name="asset_description" label="Mô tả tài sản" rules={[{ required: true, message: 'Vui lòng nhập mô tả tài sản!' }]}>
              <Input placeholder="Ví dụ: QSDĐ và tài sản gắn liền với đất..." />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="asset_type" label="Loại TS">
              <Select 
                showSearch
                placeholder="Chọn loại tài sản..."
                allowClear
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <Divider style={{ margin: '4px 0' }} />
                    <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<PlusOutlined />} 
                        style={{ width: '100%', color: '#0f6cbd', fontWeight: 600 }}
                        onClick={handleAddNewAssetType}
                      >
                        Thêm mới...
                      </Button>
                    </div>
                  </>
                )}
                options={[
                  ...(asset_types || []),
                  ...customAssetTypes
                ].map(val => ({ value: val, label: val }))}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="valuation_purpose" label="Mục đích thẩm định">
              <Select 
                showSearch
                placeholder="Chọn mục đích..."
                allowClear
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <Divider style={{ margin: '4px 0' }} />
                    <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<PlusOutlined />} 
                        style={{ width: '100%', color: '#0f6cbd', fontWeight: 600 }}
                        onClick={handleAddNewPurpose}
                      >
                        Thêm mới...
                      </Button>
                    </div>
                  </>
                )}
                options={[
                  ...(valuation_purposes || []),
                  ...customPurposes
                ].map(val => ({ value: val, label: val }))}
              />
            </Form.Item>
          </Col>
        </Row>

        {/* Section 4: Phí & Thanh toán */}
        <Divider orientation="left" style={{ margin: '12px 0', color: '#0f6cbd' }}>Phí & Thanh toán</Divider>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="valuation_fee_number" label="Phí thẩm định (VND)">
              <InputNumber style={{ width: '100%' }} formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, '.')} parser={value => value.replace(/\./g, '')} placeholder="Phí thẩm định" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="advance_payment" label="Tạm ứng">
              <Input placeholder="Tạm ứng..." />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="payment_status" label="Thanh toán">
              <Select options={payment_statuses.map(p => ({ label: p, value: p }))} />
            </Form.Item>
          </Col>
        </Row>

        {/* Section 5: Thực hiện */}
        <Divider orientation="left" style={{ margin: '12px 0', color: '#0f6cbd' }}>Thực hiện & Nghiệp vụ</Divider>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="execution_month" label="Tháng thực hiện" rules={[{ required: true, message: 'Nhập tháng thực hiện!' }]}>
              <Input placeholder="Ví dụ: 06/2026" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="valuation_staff" label="Nhân viên thẩm định">
              <Select
                showSearch
                placeholder="Chọn nhân viên"
                allowClear
                options={appraisers.map(a => ({ label: a, value: a }))}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="case_status" label="Trạng thái hồ sơ">
              <Select options={statuses.map(s => ({ label: s, value: s }))} />
            </Form.Item>
          </Col>
        </Row>


        {/* Section 7: Ghi chú */}
        <Divider orientation="left" style={{ margin: '12px 0', color: '#0f6cbd' }}>Ghi chú</Divider>
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item name="personal_note" label="Ghi chú nội bộ">
              <TextArea rows={3} placeholder="Ghi chú thêm về hồ sơ..." />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>

    <Modal
      open={newOrgOpen}
      title="Thêm mới Tổ chức"
      okText="Thêm"
      cancelText="Hủy"
      onCancel={() => {
        setNewOrgOpen(false);
        newOrgForm.resetFields();
      }}
      onOk={() => {
        newOrgForm.validateFields()
          .then(values => {
            handleCreateOrgSubmit(values);
          })
          .catch(info => {
            console.log('Validate Failed:', info);
          });
      }}
    >
      <Form
        form={newOrgForm}
        layout="vertical"
        name="new_org_form"
      >
        <Form.Item
          name="name"
          label="Tên công ty / tổ chức"
          rules={[{ required: true, message: 'Vui lòng nhập tên công ty / tổ chức!' }]}
        >
          <Input placeholder="Tên công ty / tổ chức..." />
        </Form.Item>
        <Form.Item
          name="tax_code"
          label="Mã số thuế"
        >
          <Input placeholder="Mã số thuế..." />
        </Form.Item>
        <Form.Item
          name="address"
          label="Địa chỉ"
        >
          <Input placeholder="Địa chỉ..." />
        </Form.Item>
        <Form.Item
          name="representative"
          label="Người đại diện pháp luật"
        >
          <Input placeholder="Họ và tên..." />
        </Form.Item>
        <Form.Item
          name="position"
          label="Chức vụ"
        >
          <Input placeholder="Giám đốc, Chủ tịch..." />
        </Form.Item>
      </Form>
    </Modal>
  </>
);
}
